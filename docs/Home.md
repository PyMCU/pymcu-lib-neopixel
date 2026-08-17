# pymcu-lib-neopixel

WS2812 / WS2812B ("NeoPixel") addressable LED strips for [PyMCU](https://pymcu.org).

PyMCU compiles a statically-typed, allocation-free subset of Python straight to
microcontroller machine code, ahead of time. There is no interpreter on the chip: a
"library" like this one is Python source that the compiler reads at build time, and
every call to it is either inlined away or turned into a plain subroutine call in the
final binary. What ships to the device is a `.hex` file, not a script.

This wiki covers the library, not PyMCU itself. Start with
[Getting started](Getting-started.md).

## Pages

- [Getting started](Getting-started.md) — install the library, wire an LED, build and
  flash the example.
- [The three APIs](The-three-APIs.md) — native, MicroPython-compatible and
  CircuitPython-compatible, side by side, with the same script under each.
- [How it works](How-it-works.md) — the WS2812 wire protocol, why interrupts are
  disabled during `show()`, the SRAM framebuffer and its cost, and the AVR bit timing:
  verified in simulation for eleven of the twelve supported pins, still broken on the
  twelfth (`PB0`).
- [Porting to a new architecture](Porting-to-a-new-architecture.md) — `_neopixel/avr.py`
  is the entire AVR-specific contract; what a port to another architecture has to
  provide.
- [Troubleshooting](Troubleshooting.md) — compile errors, wrong colors, nothing lights
  up, and the `PB0` timing gap.

## The library at a glance

| | |
|---|---|
| Import | `neopixel` (all three API layers) |
| Native API entry point | `from neopixel import NeoPixel` |
| Hardware supported | WS2812 / WS2812B strips on AVR (ATmega328P and friends) at 16 MHz |
| Pins | `PB0`-`PB5`, `PD2`-`PD7` (12 pins; not `PB6`/`PB7` — crystal on most AVR boards — nor `PD0`/`PD1` — UART); avoid `PB0` until its timing is fixed, see [How it works](How-it-works.md#bit-timing-measured-on-the-emulator-not-derived-from-source) |
| SRAM cost | 3 bytes per pixel, nothing else (24 bytes for a strip of 8) |
| Flash cost | See the per-example figures in [Getting started](Getting-started.md) — a fill-and-blink program compiles to well under 1 KB on an ATmega328P |
| License | MIT |

## Which API do I use?

Whichever one your script is already written against. All three read and write the
same per-strip SRAM buffer through `_neopixel/core.py`, so a native script, a
MicroPython script and a CircuitPython script that set the same pixels produce the
same bytes on the wire — see
[`test_every_layer_puts_the_same_bytes_on_the_wire`](../tests/test_neopixel.py) in the
test suite, which asserts exactly that. Details in
[The three APIs](The-three-APIs.md).
