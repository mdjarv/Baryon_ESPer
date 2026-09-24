// Report data-line state on GPIO5 once per second: % time high, edge count,
// and the longest low pulse. GPIO4 left floating (input) so nothing drives the line.
#include <Arduino.h>
#define PIN 5
void setup() {
  Serial.begin(115200);
  pinMode(4, INPUT);
  pinMode(PIN, INPUT);
}
void loop() {
  uint32_t t0 = micros(), hi = 0, n = 0, edges = 0, lowStart = 0, lowMax = 0;
  int prev = digitalRead(PIN);
  if (!prev) lowStart = t0;
  while (micros() - t0 < 1000000) {
    int v = digitalRead(PIN); uint32_t now = micros();
    n++; hi += v;
    if (v != prev) {
      edges++;
      if (!v) lowStart = now; else if (now - lowStart > lowMax) lowMax = now - lowStart;
      prev = v;
    }
  }
  if (!prev && micros() - lowStart > lowMax) lowMax = micros() - lowStart;
  Serial.printf("%lu high=%lu%% edges=%lu longest_low=%lu us\n", millis() / 1000, hi * 100 / n, edges, lowMax);
}
