/*
 * PureRoute v2 Hardware Bring-Up - Step 6: Bipolar AC Conductivity Probe Test
 * Hardware:
 *   Electrode 1: Connected to Pin D7 via 1 kΩ series resistor.
 *   Electrode 2: Connected to Pin D8 directly.
 *   Sense Node: Pin A1 connected between 1 kΩ resistor and Electrode 1.
 *   2x SS304 screws mounted 8-15 mm apart at a fixed depth mark.
 * Pass when: Air reads > 200 kΩ; tap water reads ~1.5 - 5 kΩ; salty water drops resistance; asymmetry < 20%.
 */

const byte EC_A = 7;
const byte EC_B = 8;
const byte PIN_EC = A1;
const float R_SER = 1000.0;
const float VCC_MV = 5000.0;

bool readBipolarResistance(float &rx, float &asym) {
  pinMode(EC_A, OUTPUT);
  pinMode(EC_B, OUTPUT);

  float s1 = 0, s2 = 0;
  byte n1 = 0, n2 = 0;

  for (byte i = 0; i < 8; i++) {
    // Pulse direction 1: D7 HIGH, D8 LOW
    digitalWrite(EC_A, HIGH);
    digitalWrite(EC_B, LOW);
    delayMicroseconds(400);
    float v1 = analogRead(PIN_EC) * (VCC_MV / 1023.0);

    // Pulse direction 2: D7 LOW, D8 HIGH
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

  // Return pins to high impedance to stop electrolysis
  digitalWrite(EC_A, LOW);
  digitalWrite(EC_B, LOW);
  pinMode(EC_A, INPUT);
  pinMode(EC_B, INPUT);

  if (n1 == 0 && n2 == 0) return false;
  float r1 = n1 ? (s1 / n1) : 0;
  float r2 = n2 ? (s2 / n2) : 0;

  if (n1 > 0 && n2 > 0) {
    rx = (r1 + r2) / 2.0;
    asym = fabs(r1 - r2) / rx;
  } else {
    rx = n1 ? r1 : r2;
    asym = 0.0;
  }
  return true;
}

void setup() {
  Serial.begin(115200);
  Serial.println(F("=== PUREROUTE V2 BRING-UP: STEP 6 CONDUCTIVITY TEST ==="));
  Serial.println(F("Dip SS304 screws to the marked line in test cup."));
  Serial.println(F("Format: Rx (Ohms) | Asymmetry | Status"));
}

void loop() {
  float rx = 0.0, asym = 0.0;
  bool ok = readBipolarResistance(rx, asym);

  if (!ok || rx > 200000.0) {
    Serial.print(F("Rx: > 200 kΩ (Out of water / Probe in air) --> FAULT (Air)"));
  } else if (rx < 50.0) {
    Serial.print(F("Rx: "));
    Serial.print(rx, 1);
    Serial.print(F(" Ω --> FAULT (Screws shorted)"));
  } else {
    Serial.print(F("Rx: "));
    Serial.print(rx, 1);
    Serial.print(F(" Ω | Asym: "));
    Serial.print(asym * 100.0, 1);
    Serial.print(F("%"));

    if (asym > 0.20) {
      Serial.print(F(" --> FAULT (Polarised/Fouled >20%)"));
    } else {
      Serial.print(F(" --> PASS (Clean reading)"));
    }
  }
  Serial.println();
  delay(1000);
}
