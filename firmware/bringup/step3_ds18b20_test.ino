/*
 * PureRoute v2 Hardware Bring-Up - Step 3: DS18B20 Temperature Probe Test
 * Hardware: Pin D4 with 4.7 kΩ pull-up to 5V. VCC to 5V, GND to GND.
 * Pass when: Prints steady room temperature (~20-30 °C). Fails on -127 °C or 85 °C.
 */

#include <OneWire.h>
#include <DallasTemperature.h>

const byte PIN_DS18B20 = 4;
OneWire oneWire(PIN_DS18B20);
DallasTemperature sensors(&oneWire);

void setup() {
  Serial.begin(115200);
  sensors.begin();
  sensors.setWaitForConversion(true); // Blocking for simple bring-up check
  Serial.println(F("=== PUREROUTE V2 BRING-UP: STEP 3 DS18B20 TEST ==="));
  Serial.println(F("Checking Dallas DS18B20 on Digital Pin 4..."));
  
  byte count = sensors.getDeviceCount();
  Serial.print(F("Sensors found: "));
  Serial.println(count);
  if (count == 0) {
    Serial.println(F("WARNING: No DS18B20 detected. Check 4.7k pull-up between D4 and 5V!"));
  }
}

void loop() {
  sensors.requestTemperatures();
  float t = sensors.getTempCByIndex(0);

  Serial.print(F("Temperature: "));
  Serial.print(t, 2);
  Serial.print(F(" °C  -->  "));

  if (t == -127.00) {
    Serial.println(F("FAIL: -127.00 °C (Sensor not connected or missing 4.7k pull-up)"));
  } else if (t == 85.00) {
    Serial.println(F("FAIL: 85.00 °C (Read too early / power-on reset condition)"));
  } else if (t < 0.0 || t > 50.0) {
    Serial.println(F("WARNING: Out of nominal drinking water bench range (0 - 50 °C)"));
  } else {
    Serial.println(F("PASS (Valid room/water reading)"));
  }

  delay(1000);
}
