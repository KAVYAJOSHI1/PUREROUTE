/*
 * PureRoute v2 Hardware Bring-Up - Step 4: YF-S401 Flow Sensor Test
 * Hardware: Yellow wire -> Pin D2 (Interrupt 0), Red -> 5V, Black -> GND.
 * Pass when: Pulse count rises when blowing gently or water flows.
 */

const byte PIN_FLOW = 2;
volatile unsigned long pulseCount = 0;

void onPulse() {
  pulseCount++;
}

unsigned long lastSec = 0;
float testK = 5000.0; // Benchmark default pulses per litre

void setup() {
  Serial.begin(115200);
  pinMode(PIN_FLOW, INPUT_PULLUP);
  attachInterrupt(digitalPinToInterrupt(PIN_FLOW), onPulse, FALLING);
  Serial.println(F("=== PUREROUTE V2 BRING-UP: STEP 4 FLOW SENSOR TEST ==="));
  Serial.println(F("Blow gently through YF-S401 or run the pump loop."));
  Serial.println(F("Format: Pulses/sec | Approx L/min (at K=5000)"));
}

void loop() {
  if (millis() - lastSec >= 1000) {
    lastSec = millis();
    
    noInterrupts();
    unsigned long pulses = pulseCount;
    pulseCount = 0;
    interrupts();

    float lpm = (float)pulses * 60.0 / testK;

    Serial.print(F("Pulses: "));
    Serial.print(pulses);
    Serial.print(F(" | Est. Flow: "));
    Serial.print(lpm, 2);
    Serial.print(F(" L/min"));

    if (pulses > 0) {
      Serial.println(F(" --> PASS (Flow detected)"));
    } else {
      Serial.println(F(" (Idle - 0 pulses)"));
    }
  }
}
