/*
 * PureRoute v2 Hardware Bring-Up - Step 5: Turbidity Sensor Test
 * Hardware: Turbidity module AOUT -> Pin A0 (with 100 nF capacitor from A0 to GND).
 * VCC to 5V, GND to GND. Digital out disconnected.
 * Cup wrapped in black tape against ambient light.
 * Pass when: Clear water ADC produces 4.0 - 4.5 V (never > 5V). Relative TI responds to milk drops.
 */

const byte PIN_TURB = A0;
const float VCC_MV = 5000.0; // Check with multimeter!
float v0 = 0.0;

float readMedianMv() {
  int samples[15];
  for (byte i = 0; i < 15; i++) {
    samples[i] = analogRead(PIN_TURB);
    delayMicroseconds(50);
  }
  // Insertion sort for 15 samples
  for (byte i = 1; i < 15; i++) {
    int key = samples[i];
    int j = i - 1;
    while (j >= 0 && samples[j] > key) {
      samples[j + 1] = samples[j];
      j--;
    }
    samples[j + 1] = key;
  }
  return samples[7] * (VCC_MV / 1023.0);
}

void setup() {
  Serial.begin(115200);
  Serial.println(F("=== PUREROUTE V2 BRING-UP: STEP 5 TURBIDITY TEST ==="));
  Serial.println(F("Place optical tip in clean water cup (shielded with black tape)."));
  Serial.println(F("Send 'B' to capture clear-water baseline V0."));
  delay(1000);
  v0 = readMedianMv();
  Serial.print(F("Auto-captured initial Baseline V0: "));
  Serial.print(v0, 1);
  Serial.println(F(" mV"));
}

void loop() {
  if (Serial.available() > 0) {
    char c = Serial.read();
    if (c == 'B' || c == 'b') {
      v0 = readMedianMv();
      Serial.print(F("--> NEW BASELINE V0 SAVED: "));
      Serial.print(v0, 1);
      Serial.println(F(" mV"));
    }
  }

  float mv = readMedianMv();
  float ti = 0.0;
  if (v0 > 0) {
    ti = 100.0 * (1.0 - (mv / v0));
    if (ti < 0.0) ti = 0.0;
    if (ti > 100.0) ti = 100.0;
  }

  Serial.print(F("Analog: "));
  Serial.print(mv, 1);
  Serial.print(F(" mV | Turbidity Index TI: "));
  Serial.print(ti, 1);
  Serial.print(F("% (Note: never report NTU)"));

  if (mv < 100.0) {
    Serial.println(F(" --> FAIL: < 100 mV (Unplugged or open circuit)"));
  } else if (mv > 4900.0) {
    Serial.println(F(" --> FAIL: Saturated near 5V"));
  } else {
    Serial.println(F(" --> PASS"));
  }

  delay(1000);
}
