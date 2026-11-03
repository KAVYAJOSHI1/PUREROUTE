/*
 * PureRoute v2 Hardware Bring-Up - Step 8: Fresh vs Clogged Jar Test
 * Compares flow rate and backpressure between Fresh Jar and Clogged Jar.
 * Pass when:
 *   1. Fresh jar yields steady healthy flow (e.g. 1.1 - 1.3 L/min, manometer ~5 cm).
 *   2. Clogged jar drops flow to 0.3 - 0.5 L/min (never 0), and manometer column rises to 15-25 cm.
 */

const byte PIN_FLOW = 2;
const byte PIN_PUMP = 5;
volatile unsigned long pulses = 0;

void onPulse() { pulses++; }

float kFlow = 5000.0;

void setup() {
  Serial.begin(115200);
  pinMode(PIN_PUMP, OUTPUT);
  digitalWrite(PIN_PUMP, HIGH); // Turn pump ON for flow test

  pinMode(PIN_FLOW, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(PIN_FLOW), onPulse, FALLING);

  Serial.println(F("=== PUREROUTE V2 BRING-UP: STEP 8 CARTRIDGE BENCHMARK ==="));
  Serial.println(F("Comparing Fresh vs Clogged filter flow and backpressure."));
  Serial.println(F("Ensure jar is airtight. Watch manometer tube height!"));
}

unsigned long lastTick = 0;

void loop() {
  if (millis() - lastTick >= 1000) {
    lastTick = millis();
    
    noInterrupts();
    unsigned long p = pulses;
    pulses = 0;
    interrupts();

    float flowLpm = (float)p * 60.0 / kFlow;

    Serial.print(F("Flow: "));
    Serial.print(flowLpm, 2);
    Serial.print(F(" L/min | Status: "));

    if (flowLpm > 0.80) {
      Serial.println(F("FRESH CARTRIDGE (Healthy high flow)"));
    } else if (flowLpm >= 0.30) {
      Serial.println(F("CLOGGED CARTRIDGE (Measurable drop >= 0.3 L/min --> PASS!)"));
    } else {
      Serial.println(F("BELOW SENSOR MINIMUM (<0.3 L/min - remove 1-2 cloth layers!)"));
    }
  }
}
