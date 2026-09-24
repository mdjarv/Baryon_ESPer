// Passive PSP battery-bus sniffer. GPIO5 listens only; nothing is driven.
// Each burst (bytes separated by < BURST_GAP_US) prints as one line:
//   <ms> gap=<us idle before burst> n=<bytes> ib=<min>/<max> us : <hex>
// ib = byte-to-byte spacing: ~573 us => 1 stop bit, ~625 us => 2 stop bits @19200 8E.
#include <Arduino.h>

#define RX_PIN 5
#define TX_PIN 7            // unused pin; keeps UART1 TX away from GPIO4
#define BURST_GAP_US 2000

uint8_t buf[256];
uint32_t tFirst, tLast, tPrevBurstEnd, ibMin, ibMax;
int n = 0;

void flushBurst() {
  if (!n) return;
  Serial.printf("%lu gap=%lu n=%d ib=%lu/%lu us :", tFirst / 1000, tFirst - tPrevBurstEnd, n,
                n > 1 ? ibMin : 0, n > 1 ? ibMax : 0);
  for (int i = 0; i < n; i++) Serial.printf(" %02X", buf[i]);
  Serial.println();
  tPrevBurstEnd = tLast;
  n = 0;
}

void setup() {
  Serial.begin(115200);
  delay(1000);
  Serial1.begin(19200, SERIAL_8E1, RX_PIN, TX_PIN);
  bool fifoOk = Serial1.setRxFIFOFull(1);   // per-byte timestamps; must follow begin()
  Serial.printf("PSP bus sniffer: RX=GPIO5, 19200 8E1, passive, fifo1=%d\n", fifoOk);
}

void loop() {
  while (Serial1.available()) {
    uint32_t now = micros();
    uint8_t b = Serial1.read();
    if (n && now - tLast > BURST_GAP_US) flushBurst();
    if (n == 0) { tFirst = now; ibMin = UINT32_MAX; ibMax = 0; }
    else { uint32_t d = now - tLast; if (d < ibMin) ibMin = d; if (d > ibMax) ibMax = d; }
    if (n < (int)sizeof(buf)) buf[n++] = b;
    tLast = now;
  }
  if (n && micros() - tLast > BURST_GAP_US) flushBurst();
}
