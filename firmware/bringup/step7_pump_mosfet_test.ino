/*
 * PureRoute v2 Hardware Bring-Up - Step 7: Pump & MOSFET Driver Test
 * Hardware:
 *   Uno Pin D5 -> MOSFET IN (with 10 kΩ pull-down from D5 to GND).
 *   MOSFET VIN+ / VIN- -> Dedicated 5V 2A supply (with 470-1000 µF capacitor).
 *   MOSFET OUT+ / OUT- -> Pump (with 1N5819 / 1N4007 flyback diode across pump).
 *   Shared ground between Pump 5V supply and Uno GND.
 * Pass when: Pump turns ON for 3s, OFF for 3s without causing Uno brownout or USB disconnect.
 */

const byte PIN_PUMP = 5;

void setup() {
  pinMode(PIN_PUMP, OUTPUT);
  digitalWrite(PIN_PUMP, LOW); // Stay OFF during boot

  Serial.begin(115200);
  Serial.println(F("=== PUREROUTE V2 BRING-UP: STEP 7 PUMP & MOSFET TEST ==="));
  Serial.println(F("Testing 3-second ON / 3-second OFF cycling."));
  Serial.println(F("Watch the Uno power LED: it MUST NOT flicker or reboot!"));
}

void loop() {
  Serial.println(F("Pump: [ON] (Pin D5 HIGH)"));
  digitalWrite(PIN_PUMP, HIGH);
  delay(3000);

  Serial.println(F("Pump: [OFF] (Pin D5 LOW)"));
  digitalWrite(PIN_PUMP, LOW);
  delay(3000);
}
