# PSP-1001 debugging log (ESP32-C3 SuperMini)

Notes from getting Baryon ESPer to talk to a soft-bricked PSP-1001, 2026-09-24.
The PSP now authenticates the ESP as a battery and auto-powers on in service
mode. It has not booted DC-ARK yet: it resets about 1 s after power-on (see
[Open issue](#open-issue-reset-1-s-after-power-on)).

## Setup

| Part | Detail |
|---|---|
| PSP | PSP-1001, soft brick (power LED on, then off). Syscon key version `0x00` |
| MCU | ESP32-C3 SuperMini, flashed with `arduino-cli`, core `esp32:esp32` 3.3.12, `CDCOnBoot=cdc` |
| Power | Otii Arc as the battery: + and − to the PSP battery terminal |
| Logging | ESP USB serial, `serial capture`, Otii recordings |

Flash command:

```
mkdir -p /tmp/ESPer && cp ESPer.ino /tmp/ESPer/
arduino-cli compile -u -p /dev/ttyACM1 -b esp32:esp32:esp32c3:CDCOnBoot=cdc /tmp/ESPer
```

### Wiring (as used now)

```
3V3 ──[10k]──┬── GPIO5 (RX)
             ├── GPIO4 (TX, open-drain)   plain jumper, no diode
             └── PSP terminal middle pin (data)

Otii + ─────────── PSP terminal +
Otii − ──┬──────── PSP terminal −
ESP GND ─┘
```

SuperMini pin positions (USB-C up, chip side): GPIO5 is top left; 3.3 and GPIO4
are 3rd and 4th on the right. The pins labelled RX/TX (GPIO20/21) are UART0 and
are not used.

## What was wrong, and the fixes

Each fix below changed what the PSP did. Items 3–5 were confirmed by sniffing a
genuine Sony battery on the bus.

### 1. A red LED does not work as the diode

The README circuit uses a diode from GPIO4 to the data line. A red LED drops
~1.8 V, so the line never goes below ~1.7 V when GPIO4 is low. The log showed
`[echo] wanted 7, got 1..4` and the PSP repeated `5A 02 01` forever.

Fix: GPIO4 is now set open-drain in firmware (`gpio_od_enable()` after
`Serial1.begin()`) and jumpered straight to GPIO5. A real diode (1N4148, BAT85)
still works with this firmware.

### 2. The Otii was capped at 3.7 V

With 3.7 V on the + pin (a nearly empty Li-ion cell), syscon charged the
"battery" but never powered on. With `Main current` set to **High range** the
Otii accepts higher voltages; 4.1 V is what we use now. Battery-only insertion
at 4.1 V makes the PSP auto-power on, as a JigKick should.

On DC, the charge LED (orange) hides the green power LED. A PSP that seems
"only charging" may already be on; unplugging the Otii shows green.

### 3. Wrong challenge-2 secrets and 0x81 answer length for PSP-1000

`pysweeper` (and ESPer, which copied it) has the `challenge1_secret` /
`challenge2_secret` entries for key versions `0x01`–`0x06` shifted, and the
wrong `challenge2_secret` for `0x00`. It also answers opcode `0x81` with 16
bytes. The PSP rejected every attempt: on DC it charged and re-authenticated
every 500 ms; on battery alone it retried 32 times, then clamped the data line
low and locked out.

Sniffing a genuine battery (`tools/Sniffer`) gave two complete exchanges:

| PSP `0x80` (version + nonce) | Battery reply | PSP `0x81` data | Battery reply |
|---|---|---|---|
| `00 E1BCF9274831B390` | `92509309BA806FB2 BE97DA6B4634FA94` | `0129832D8BEFE2BA` | `A5 0A 06 5BB11883B940A1EF 1A` |
| `00 BED3E335975F084D` | `3900087B53E7620E 470D9535E4E66C8B` | `B9F85F16C931BE74` | `A5 0A 06 4A915D59B23688DF 6A` |

- The first 8 bytes of the `0x80` reply matched our math, so key `0x00` and
  challenge 1 were right.
- The second 8 bytes are the battery's own nonce.
- The `0x81` reply is **8 bytes** (`A5 0A 06`), not 16.

[Yoti's piesweeper](https://github.com/Yoti/piesweeper) has the corrected
tables and sends `'a50a06' + response2[0:8]`. With `challenge2_secret[0x00] =
f4e04313ad2eb4db` it reproduces both genuine `0x81` replies byte for byte
(`tools/cmp_pie.py`). ESPer now uses piesweeper's secrets for `0x00`–`0x06` and
sends 8 bytes for those versions. Newer versions keep the 16-byte form.

Other bus facts from the capture:

- A PSP-1000 sends 8E1 frames back to back (571 µs per byte at 19200 baud).
- A genuine battery replies about 4.5 ms after a request.
- With a genuine battery on DC, the PSP re-checks it roughly every 18 s. Our
  broken emulator was re-checked every 500 ms: that rhythm means rejection.
- Periodic checks skip the serial number: `01 → 80 → 81`.

### 4. Battery status (`0x01`) reply

pysweeper answers `0x01` with `10 C3 06`. On this PSP that produced a flashing
green power LED (low battery) and no boot. The genuine battery sent `00 C3 05`,
`10 C0 05`, `00 CB 05` (the last two bytes rise while charging). ESPer now
sends the captured `A5 05 06 00 C3 05 87`. The next run gave a solid green LED.

### 5. USB logging made replies late

The firmware printed each packet over USB before answering. A stalled USB
write pushed replies past the PSP's timeout, and the PSP talked over them
(`[echo] wanted 12, got 1`). Now:

- replies are transmitted first, then logged;
- log text is buffered and written only when the bus has been idle for 20 ms,
  without blocking (`flushLog()`, `setTxTimeoutMs(0)`, 4 KB TX buffer);
- `REPLY_DELAY_MS` is 2 ms.

### 6. The Magic Memory Stick

- The first card (64 GB microSD in an adapter) had no DDC/ARK files, only a
  stock PSP folder layout.
- A 16 GB card was rebuilt with an active FAT32 partition at sector 2048, the
  ARK-4 `TM` folder, and the 6.61 flash files extracted with
  [pspdecrypt](https://github.com/John-K/pspdecrypt) (built from source: the
  release binary needs OpenSSL 1.1).
- krazynez's DC-ARK-Maker `msipl.bin` targets newer models. ARK-4's own
  `PC/MagicMemoryCreator` has a "Legacy IPL (1000s and early 2000s ONLY!)"
  option that writes `tm_msipl_legacy.bin`. The card now has the legacy IPL.

## Open issue: reset ~1 s after power-on

With authentication passing, the PSP powers on and then shuts down about 1 s
later. It does this:

- in service mode with the stick, without the stick, and with the legacy IPL;
- in normal mode (serial `12345678`) after a power-switch flick.

On DC alone, the same PSP stays on (green) indefinitely. In service mode the
JigKick auto-boot retries, giving a ~1.2 s loop:

```
01 0C 80 81     full handshake after power-on
01 80 81        re-check
01 80           reply cut off mid-packet (PSP drops the line), then repeat
```

Some runs show a solid green LED with ~50 mA baseline; others show a flashing
green LED (low battery) with ~0 mA baseline and a ~45 mA blip every 1.5 s. The
run-to-run variation points at supply voltage rather than protocol.

Leading hypothesis: voltage sag at the PSP. The Otii regulates 4.1 V at its own
terminals; breadboard and Dupont wiring can lose several hundred mV when the
main system powers up, which syscon sees as a flat battery.

## Next steps

1. **Power delivery.** Run short, thick leads from the Otii straight to the
   PSP + and − pins (no breadboard). Enable Otii 4-wire sensing with the sense
   leads at the PSP terminal, or record the `Sense+ voltage` channel there to
   see the dip. Try 4.2 V.
2. **Physical Pandora battery.** Hardmod a genuine PSP-1000 battery by lifting
   the ground pin of its serial EEPROM (IC104 / IC04 / C04 near the contacts,
   see the [psdevwiki JigKick page](https://www.psdevwiki.com/psp/JigKick_Battery)).
   It then reports `FFFFFFFF` and does its own authentication, which rules out
   both the emulator and the power path. If that also resets after ~1 s, the
   problem is the PSP (board or NAND), not the emulator.
3. **Memory stick.** If the PSP stays on but DC-ARK does not load, try a
   genuine Sony Memory Stick Pro Duo, and compare `msipl.bin` with
   `tm_msipl_legacy.bin` again.
4. **Status reply.** The `0x01` payload probably carries remaining capacity.
   If low-battery blinking comes back with good power, try `00 CB 05` (a higher
   captured value) or decode the fields from more captures.

## Tools

All in `tools/`. Arduino sketches build with the same `arduino-cli` command as
ESPer.

| Tool | Purpose |
|---|---|
| `Sniffer/` | Passive bus sniffer on GPIO5. Prints each burst with idle gap and byte spacing. Used for the genuine-battery capture |
| `Bridge/` | USB CDC ↔ PSP bus bridge (open-drain TX), so PC tools like pysweeper can drive the bus |
| `LineProbe/` | Reports data-line level, edge count and longest low pulse each second. Found the lockout (line held at 0 V) |
| `run_pysweeper.py` | Runs khubik2's pysweeper unmodified without its Tk window and logs to stdout |
| `cmp_genuine.py` | Compares pysweeper's challenge math with the genuine captures |
| `cmp_pie.py` | Checks piesweeper's `0x81` formula against the genuine captures |
| `esplog.py` | Timestamped serial logger that survives USB re-enumeration |

## References

- [khubik2/pysweeper](https://github.com/khubik2/pysweeper), and
  [issue #28](https://github.com/khubik2/pysweeper/issues/28): the handshake
  loop also happens when the stick isn't bootable
- [Yoti/piesweeper](https://github.com/Yoti/piesweeper): corrected secret
  tables, 8-byte `0x81` answer
- [PSP-Archive/ARK-4](https://github.com/PSP-Archive/ARK-4): DC-ARK,
  MagicMemoryCreator, legacy IPL
- [psdevwiki: JigKick Battery](https://www.psdevwiki.com/psp/JigKick_Battery)
