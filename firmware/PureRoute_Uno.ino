/*
 * PureRoute v2 Decision Engine - Arduino Uno Firmware
 * Platform: ATmega328P (Arduino Uno)
 * Baud: 115200
 *
 * Pins:
 *   DS18B20 Temp: 4
 *   Flow Sensor:  2 (Interrupt 0)
 *   Turbidity:    A0
 *   EC Probe ADC: A1
 *   EC Pulse A:   7
 *   EC Pulse B:   8
 *   EC Ground:    9
 *   Pump Relay:   5
 *   LED UF:       10 (Green)
 *   LED RO:       11 (Blue)
 *   LED YEL:      12 (Yellow)
 *   LED RED:      13 (Red)
 */

#include <OneWire.h>
#include <DallasTemperature.h>
#include <EEPROM.h>
#include <avr/wdt.h>

const byte PIN_T = 4;
const byte PIN_FLOW = 2;
const byte PIN_TURB = A0;
const byte PIN_EC = A1;
const byte EC_A = 7;
const byte EC_B = 8;
const byte EC_LO = 9;

const byte PIN_PUMP = 5;
const byte LED_UF = 10;
const byte LED_RO = 11;
const byte LED_YEL = 12;
const byte LED_RED = 13;

const float R_SER = 1000.0;
const float VCC_MV = 5000.0; // Calibrate to measured 5V rail

const float T_HI = 25.0;
const float T_LO = 10.0;
const float TURB_MARGIN = 5.0;
const float EC_SWITCH_IN = 500.0;
const float EC_SWITCH_OUT = 450.0;

struct Cal {
  float kFlow; // pulses per litre (~5000)
  float v0;    // clear-water turbidity baseline mV
  float q0;    // fresh cartridge flow L/min
  float ecA;
  float ecB;
  float ecC;
} cal;

OneWire ow(PIN_T);
DallasTemperature ds(&ow);

volatile unsigned long flowPulseCount = 0;
void onPulse() {
  flowPulseCount++;
}

bool areaLocked = false;
byte pumpState = 1; // Default requested pump state (1=ON, 0=OFF)
char sampleTag[16] = "INIT";

enum State { UF_UV, RO_STATE, FLUSH, REPLACE, LOCKED_RO, FAULT };
State currentState = UF_UV;
State candidateState = UF_UV;
byte candidateCount = 0;

// Filter health & litres
float emaFlow = 0.0;
float emaFhi = 100.0;
float totalLitres = 0.0;
const float RATED_LITRES = 50.0;

// Fault monitoring counters
byte dryRunSeconds = 0;
byte leakSeconds = 0;
byte faultClearSeconds = 0;

// Stuck sensor tracking (last 30 samples)
float lastTurbMv = 0;
byte stuckTurbCount = 0;

unsigned long lastTickMs = 0;
bool blinkState = false;

float medianMv(byte pin) {
  int v[15];
  for (byte i = 0; i < 15; i++) {
    v[i] = analogRead(pin);
  }
  for (byte i = 1; i < 15; i++) {
    int k = v[i];
    int j = i - 1;
    while (j >= 0 && v[j] > k) {
      v[j + 1] = v[j];
      j--;
    }
    v[j + 1] = k;
  }
  return v[7] * (VCC_MV / 1023.0);
}

bool ecBurst(float &rx, float &asym) {
  pinMode(EC_A, OUTPUT);
  pinMode(EC_B, OUTPUT);
  pinMode(EC_LO, OUTPUT);
  digitalWrite(EC_LO, LOW);

  float s1 = 0, s2 = 0;
  byte n1 = 0, n2 = 0;

  for (byte i = 0; i < 8; i++) {
    digitalWrite(EC_A, HIGH);
    digitalWrite(EC_B, LOW);
    delayMicroseconds(400);
    float v1 = analogRead(PIN_EC) * (VCC_MV / 1023.0);

    digitalWrite(EC_A, LOW);
    digitalWrite(EC_B, HIGH);
    delayMicroseconds(400);
    float v2 = analogRead(PIN_EC) * (VCC_MV / 1023.0);

    if (v1 > 100 && v1 < 4900) {
      s1 += R_SER * v1 / (VCC_MV - v1);
      n1++;
    }
    if (v2 > 100 && v2 < 4900) {
      s2 += R_SER * (VCC_MV - v2) / v2;
      n2++;
    }
  }

  digitalWrite(EC_A, LOW);
  digitalWrite(EC_B, LOW);
  pinMode(EC_A, INPUT);
  pinMode(EC_B, INPUT);

  if (!n1 && !n2) return false;
  float r1 = n1 ? (s1 / n1) : 0;
  float r2 = n2 ? (s2 / n2) : 0;

  if (n1 && n2) {
    rx = (r1 + r2) / 2.0;
    asym = fabs(r1 - r2) / rx;
  } else {
    rx = n1 ? r1 : r2;
    asym = 0.0;
  }
  return true;
}

void loadDefaultsIfUnset() {
  EEPROM.get(0, cal);
  if (isnan(cal.kFlow) || cal.kFlow < 1000.0 || cal.kFlow > 10000.0) {
    cal.kFlow = 5000.0;
    cal.v0 = 2000.0;
    cal.q0 = 1.20;
    cal.ecA = 0.0;
    cal.ecB = 700000.0; // Cell constant scale G (Siemens) -> uS/cm
    cal.ecC = 0.0;
    EEPROM.put(0, cal);
  }
}

void saveCal() {
  EEPROM.put(0, cal);
}

void handleSerialCommands() {
  while (Serial.available() > 0) {
    char c = Serial.read();
    if (c == 'B') {
      cal.v0 = medianMv(PIN_TURB);
      saveCal();
    } else if (c == 'F') {
      if (emaFlow > 0.2) {
        cal.q0 = emaFlow;
        saveCal();
      }
    } else if (c == 'K') {
      float k = Serial.parseFloat();
      if (k > 1000.0) {
        cal.kFlow = k;
        saveCal();
      }
    } else if (c == 'P') {
      int p = Serial.parseInt();
      pumpState = (p == 1) ? 1 : 0;
    } else if (c == 'L') {
      int l = Serial.parseInt();
      areaLocked = (l == 1);
    } else if (c == 'S') {
      byte idx = 0;
      delay(5);
      while (Serial.available() > 0 && idx < 15) {
        char sc = Serial.read();
        if (sc == '\n' || sc == '\r') break;
        sampleTag[idx++] = sc;
      }
      sampleTag[idx] = '\0';
    }
  }
}

void updateLEDs(State s, bool blink) {
  // Turn all off first
  digitalWrite(LED_UF, LOW);
  digitalWrite(LED_RO, LOW);
  digitalWrite(LED_YEL, LOW);
  digitalWrite(LED_RED, LOW);

  switch (s) {
    case FAULT:
      digitalWrite(LED_RED, HIGH);
      break;
    case LOCKED_RO:
      if (blink) digitalWrite(LED_RO, HIGH);
      break;
    case REPLACE:
      digitalWrite(LED_YEL, HIGH);
      break;
    case FLUSH:
      if (blink) digitalWrite(LED_YEL, HIGH);
      break;
    case RO_STATE:
      digitalWrite(LED_RO, HIGH);
      break;
    case UF_UV:
      digitalWrite(LED_UF, HIGH);
      break;
  }
}

void setup() {
  pinMode(PIN_PUMP, OUTPUT);
  digitalWrite(PIN_PUMP, LOW); // Safe start: Pump OFF

  pinMode(LED_UF, OUTPUT);
  pinMode(LED_RO, OUTPUT);
  pinMode(LED_YEL, OUTPUT);
  pinMode(LED_RED, OUTPUT);

  Serial.begin(115200);
  ds.begin();
  ds.setWaitForConversion(false);
  ds.requestTemperatures();

  loadDefaultsIfUnset();

  pinMode(PIN_FLOW, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(PIN_FLOW), onPulse, FALLING);

  wdt_enable(WDTO_2S);

  Serial.println(F("t_ms,temp_c,flow_lpm,pulses,turb_mv,turb_index_pct,ec25_uScm,tds_ppm,fhi,counter_life_pct,pump,lock,state,reason,tag"));
}

void loop() {
  wdt_reset();
  handleSerialCommands();

  unsigned long now = millis();
  if (now - lastTickMs < 1000) {
    return;
  }
  lastTickMs = now;
  blinkState = !blinkState;

  // 1. Read Flow Pulses atomically
  noInterrupts();
  unsigned long pulses = flowPulseCount;
  flowPulseCount = 0;
  interrupts();

  float rawFlowLpm = (float)pulses * 60.0 / cal.kFlow;
  emaFlow = (0.2 * rawFlowLpm) + (0.8 * emaFlow);

  if (pumpState == 1 && emaFlow > 0.05) {
    totalLitres += (emaFlow / 60.0);
  }
  float counterLifePct = max(0.0, 100.0 * (1.0 - (totalLitres / RATED_LITRES)));

  // 2. Read Temperature (non-blocking DS18B20)
  float tempC = ds.getTempCByIndex(0);
  ds.requestTemperatures(); // Request next reading

  // 3. Read Turbidity
  float turbMv = medianMv(PIN_TURB);
  float turbIndexPct = 0.0;
  if (cal.v0 > 0) {
    turbIndexPct = max(0.0, min(100.0, 100.0 * (1.0 - (turbMv / cal.v0))));
  }

  // 4. Read Conductivity (Bipolar AC)
  float rxOhms = 0.0, rxAsym = 0.0;
  bool ecOk = ecBurst(rxOhms, rxAsym);
  float ec25 = 0.0;
  if (ecOk && rxOhms > 50.0 && rxOhms < 200000.0) {
    float g = 1.0 / rxOhms;
    float ec = cal.ecA + (cal.ecB * g) + (cal.ecC * g * g);
    float tComp = 1.0 + 0.019 * (tempC - 25.0);
    if (tComp > 0) ec25 = ec / tComp;
  }
  float tdsPpm = ec25 * 0.6;

  // 5. Calculate FHI
  float rawFhi = 100.0;
  if (cal.q0 > 0) {
    rawFhi = 100.0 * max(0.0, min(1.0, emaFlow / cal.q0));
  }
  emaFhi = (0.2 * rawFhi) + (0.8 * emaFhi);

  // 6. Check Faults
  bool fault = false;
  const char* faultReason = "";

  if (pumpState == 1 && emaFlow < 0.05) {
    if (++dryRunSeconds >= 3) {
      fault = true;
      faultReason = "NO FLOW >3s pump ON -> dry run";
    }
  } else {
    dryRunSeconds = 0;
  }

  if (pumpState == 0 && emaFlow > 0.10) {
    if (++leakSeconds >= 3) {
      fault = true;
      faultReason = "LEAK/SIPHON flow with pump OFF";
    }
  } else {
    leakSeconds = 0;
  }

  if (tempC == -127.0 || tempC == 85.0 || tempC < 0.0 || tempC > 50.0) {
    fault = true;
    faultReason = "TEMP SENSOR FAULT";
  }

  if (turbMv < 100.0 || turbMv > 2400.0) {
    fault = true;
    faultReason = "TURBIDITY ADC OUT OF BOUNDS";
  }

  if (rxOhms > 200000.0) {
    fault = true;
    faultReason = "EC PROBE IN AIR";
  } else if (rxOhms < 50.0 && rxOhms > 0.0) {
    fault = true;
    faultReason = "EC PROBE SHORTED";
  } else if (rxAsym > 0.20) {
    fault = true;
    faultReason = "EC PROBE POLARIZED/FOULED";
  }

  // Stuck sensor tracking: unchanged reading over 30 samples while pump runs
  if (pumpState == 1) {
    if (fabs(turbMv - lastTurbMv) < 0.5) {
      if (++stuckTurbCount >= 30) {
        fault = true;
        faultReason = "STUCK SENSOR (turbidity unchanged 30s)";
      }
    } else {
      stuckTurbCount = 0;
      lastTurbMv = turbMv;
    }
  } else {
    stuckTurbCount = 0;
  }

  // 7. Determine Raw State
  State rawState;
  const char* rawReason;

  if (fault) {
    rawState = FAULT;
    rawReason = faultReason;
  } else if (areaLocked) {
    rawState = LOCKED_RO;
    rawReason = "Area flag set -> RO forced";
  } else if (emaFhi < 40.0 || (pumpState == 1 && emaFlow < 0.30)) {
    rawState = REPLACE;
    rawReason = "FHI < 40 -> REPLACE filter";
  } else if (turbIndexPct > T_HI) {
    rawState = FLUSH;
    rawReason = "TI > 25% -> FLUSH prefilter";
  } else if (!ecOk || ec25 > EC_SWITCH_IN) {
    rawState = RO_STATE;
    rawReason = "EC25 > 500 -> RO+UV";
  } else if (ec25 <= EC_SWITCH_IN && turbIndexPct < T_LO) {
    rawState = UF_UV;
    rawReason = "Clean water -> UF+UV";
  } else {
    rawState = RO_STATE;
    rawReason = "Safe default -> RO+UV";
  }

  // 8. 5-Second Persistence & Hysteresis
  bool canExit = true;
  if (currentState == FAULT) {
    if (!fault) {
      if (++faultClearSeconds < 5) canExit = false;
    } else {
      faultClearSeconds = 0;
      canExit = false;
    }
  } else if (currentState == REPLACE) {
    if (emaFhi <= 50.0) canExit = false;
  } else if (currentState == FLUSH) {
    if (turbIndexPct >= (T_HI - TURB_MARGIN)) canExit = false;
  } else if (currentState == RO_STATE && rawState == UF_UV) {
    if (ec25 >= EC_SWITCH_OUT) canExit = false;
  }

  State target = canExit ? rawState : currentState;

  if (target != currentState) {
    if (candidateState == target) {
      if (++candidateCount >= 5) {
        currentState = target;
        candidateCount = 0;
      }
    } else {
      candidateState = target;
      candidateCount = 1;
    }
  } else {
    candidateCount = 0;
  }

  // 9. Actuator Outputs
  byte actualPump = (currentState == FAULT) ? 0 : pumpState;
  digitalWrite(PIN_PUMP, actualPump ? HIGH : LOW);
  updateLEDs(currentState, blinkState);

  // 10. Print CSV Telemetry
  const char* stateStr = "UF+UV";
  if (currentState == FAULT) stateStr = "FAULT";
  else if (currentState == LOCKED_RO) stateStr = "LOCKED_RO";
  else if (currentState == REPLACE) stateStr = "REPLACE";
  else if (currentState == FLUSH) stateStr = "FLUSH";
  else if (currentState == RO_STATE) stateStr = "RO";

  Serial.print(now); Serial.print(',');
  Serial.print(tempC, 2); Serial.print(',');
  Serial.print(emaFlow, 2); Serial.print(',');
  Serial.print(pulses); Serial.print(',');
  Serial.print(turbMv, 1); Serial.print(',');
  Serial.print(turbIndexPct, 1); Serial.print(',');
  Serial.print(ec25, 1); Serial.print(',');
  Serial.print(tdsPpm, 1); Serial.print(',');
  Serial.print(emaFhi, 1); Serial.print(',');
  Serial.print(counterLifePct, 1); Serial.print(',');
  Serial.print(actualPump); Serial.print(',');
  Serial.print(areaLocked ? 1 : 0); Serial.print(',');
  Serial.print(stateStr); Serial.print(',');
  Serial.print(rawReason); Serial.print(',');
  Serial.println(sampleTag);
}
