# Troubleshooting

## `CompileError: NeoPixel timing is only implemented for AVR`

You're building for a chip whose `__CHIP__.arch` isn't `"avr"` — this library only
supports AVR today (`pymcu.toml`: `arch = ["avr"]`). There's no workaround at the
library level; see [Porting to a new architecture](Porting-to-a-new-architecture.md)
if you want to add support for your target.

## `CompileError: NeoPixel: unsupported data pin -- use PB0-PB5 or PD2-PD7`

The pin string passed to `NeoPixel(...)` isn't one of the twelve pins the AVR driver
matches on. Two common causes:

- You passed an Arduino-style pin number instead of a port string to the **native**
  API — `NeoPixel("PD6", 8)` is correct, `NeoPixel(6, 8)` is not. If you want to use
  Arduino pin numbers, use the MicroPython-compatible API instead:
  `NeoPixel(Pin(6), 8)`.
- You picked `PB6`, `PB7`, `PD0` or `PD1`. `PB6`/`PB7` carry the crystal on most AVR
  boards and `PD0`/`PD1` are the UART RX/TX pins the bootloader and `print()`-style
  debugging use — both are deliberately excluded. Pick a different pin.

`PB0` compiles without error but currently has bad bit timing — see
[Pixels light up, but the colors are wrong or random](#pixels-light-up-but-the-colors-are-wrong-or-random)
below.

## Nothing lights up

In roughly this order:

1. **Missing `show()` / `write()`.** Every API in this library buffers pixel writes
   in SRAM and only sends them to the strip when you call `show()` (native,
   CircuitPython with `auto_write=False`) or `write()` (MicroPython). CircuitPython
   with the default `auto_write=True` sends on every write automatically — see
   [How it works: `auto_write`](How-it-works.md#auto_write).
2. **Power.** The strip's `5V` and `GND` need their own supply capable of the
   strip's peak current — a board's onboard regulator is rarely rated for more than a
   few pixels at full brightness. See [Getting started](Getting-started.md#wire-it-up).
3. **Wrong pin, or the pin argument doesn't match your wiring.** Double check the
   pin passed to `NeoPixel(...)` against where `DIN` is actually connected.
4. **Ground not shared.** If the strip has a separate 5V supply from the board, the
   two grounds still need to be tied together, or the data signal has no common
   reference.

## Pixels light up, but the colors are wrong or random

**If your data pin is `PB0`, that's the cause — stop there.** Eleven of the twelve
pins this driver supports have verified bit timing; `PB0` alone still runs the
original, unpadded encoding (measured on the emulator at 312.5 ns / 250 ns — both
inside the same window, so the strip can't tell a 0-bit from a 1-bit). Use a different
pin, or fix `_ws2812_b`'s `case 0:` yourself to match `case 1:` (see
[How it works: bit timing](How-it-works.md#bit-timing-measured-on-the-emulator-not-derived-from-source)).

For every other supported pin, the AVR bit encoding (`_neopixel_avr.py`) is verified
in simulation against both the WS2812 and WS2812B timing windows — see the same
section above for the measured numbers and `tests/test_timing.py`, which fails if a
future change narrows the margin again. That verification is on a cycle-accurate
emulator, not a real strip on a scope, so if colors are still wrong on a pin other
than `PB0`, look at the ordinary causes first:

- **Channel order.** All three APIs take colors as `(r, g, b)` and convert to the
  WS2812 wire order (GRB) internally — if you're seeing red where you set blue, check
  you're not accidentally passing already-reordered tuples.
- **First pixel(s) look right, the rest don't (or vice versa).** This is consistent
  with a single corrupted byte early in the stream throwing off every byte after it —
  which is exactly the failure mode WS2812's shift-register design produces from any
  timing error, and exactly what disabling interrupts during `show()` is meant to
  prevent (see [How it works](How-it-works.md#why-interrupts-are-disabled)). If you
  have something else running with interrupts that `show()` doesn't account for (a
  watchdog, a second core on a multi-core target), that's a candidate.
- **Power.** A strip that's browning out under load (see
  [Random flicker](#random-flicker-or-the-whole-strip-resets-partway-through-a-pattern)
  below) can also read as wrong colors on the pixels nearest the far end of a long run,
  not just outright resets.
- **Level shifting.** AVR boards this library targets run 5V logic, matching WS2812's
  expected `DIN` level, so this isn't a concern on the boards this library supports
  today — but if you've adapted the wiring to a 3.3V board, an unreliable high level on
  `DIN` produces exactly this symptom, and needs a level shifter, not a software fix.
- **A bad connection or a damaged first pixel.** Since every pixel re-transmits for
  the ones after it, a marginal solder joint or a first LED damaged by static/reversed
  polarity can corrupt everything downstream while looking, from the code's
  perspective, like nothing is wrong.

If none of that explains it, that's worth reporting — the emulator verification covers
the instruction timing the compiler generates, not every failure mode a real strip can
have.

## Random flicker, or the whole strip resets partway through a pattern

Usually a supply issue (brief brownout under load as more pixels turn on) rather than
anything this library controls. Add bulk capacitance near the strip's power input and
confirm the supply is rated for the strip's actual peak draw.

## Building `examples/circuitpython_basic` or `examples/auto_write` prints a warning about a shadowed module

Expected — see
[The three APIs: a note on the CircuitPython examples](The-three-APIs.md#a-note-on-the-circuitpython-examples).
The build still succeeds and the example still runs the CircuitPython API correctly;
the warning is about which copy of the driver code actually got compiled.

## `pymcu lint --library ... --write-surface` says the API surface changed after I only touched an example

`[library.examples]` in `pymcu.toml` is part of the tracked public surface (it's what
`pymcu install` and the docs site show as "what this library ships"), so adding or
renaming an example trips the same check as changing a function signature. Re-run
lint with `--write-surface` to refresh `api-surface.lock`, and bump the distribution
version as the lint output asks if you're about to publish.
