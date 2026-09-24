// USB CDC <-> PSP one-wire bus bridge, so PC tools (pysweeper) can drive the bus.
// Wiring as ESPer: GPIO4 (open-drain TX) jumpered to GPIO5 (RX), 10k pull-up to 3V3.
// TX bytes are echoed back by the wire, which pysweeper expects.
#include <Arduino.h>
#include "esp_private/gpio.h"

#define RX_PIN 5
#define TX_PIN 4

void setup() {
  Serial.begin(115200);                       // USB CDC; host baud is ignored
  Serial1.begin(19200, SERIAL_8E1, RX_PIN, TX_PIN);
  Serial1.setRxFIFOFull(1);
  gpio_od_enable((gpio_num_t)TX_PIN);
}

void loop() {
  while (Serial.available()) {                // PC -> PSP, padded to 2 stop bits
    Serial1.write((uint8_t)Serial.read());
    Serial1.flush();
    delayMicroseconds(60);
  }
  while (Serial1.available()) Serial.write((uint8_t)Serial1.read());  // PSP -> PC
}
