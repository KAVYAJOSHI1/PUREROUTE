/*
 * PureRoute v2 Hardware Bring-Up - Step 2: Serial Link Test
 * Connect Uno to Laptop USB. Open Arduino IDE Serial Monitor or dashboard at 115200 baud.
 * Pass when: Greeting banner arrives clearly without garbage characters, and echoes received text.
 */

void setup() {
  Serial.begin(115200);
  while (!Serial) { ; }
  delay(200);
  Serial.println(F("=== PUREROUTE V2 BRING-UP: STEP 2 SERIAL TEST ==="));
  Serial.println(F("Status: Arduino Uno USB Serial Connected OK @ 115200 Baud"));
  Serial.println(F("Type any character into Serial Monitor to test loopback echo."));
}

unsigned long lastTick = 0;
unsigned long seconds = 0;

void loop() {
  if (Serial.available() > 0) {
    char c = Serial.read();
    Serial.print(F("Echo: ["));
    Serial.print(c);
    Serial.println(F("] OK"));
  }

  if (millis() - lastTick >= 1000) {
    lastTick = millis();
    seconds++;
    Serial.print(F("Heartbeat uptime: "));
    Serial.print(seconds);
    Serial.println(F(" s"));
  }
}
