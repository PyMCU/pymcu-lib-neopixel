# Getting started

## Install

```bash
pymcu install neopixel
```

This adds `pymcu-lib-neopixel` to your project's dependencies and makes `import
neopixel` resolve for the compiler. There is nothing to configure: the library has no
runtime settings, only the pin and pixel count you pass to `NeoPixel(...)` in your own
code.

## Wire it up

Any of `PB0`-`PB5` or `PD2`-`PD7` works as the data pin (see
[How it works](How-it-works.md) for why the other pins on an ATmega328P are excluded)
— except `PB0`, whose timing is not yet fixed; see
[How it works: bit timing](How-it-works.md#bit-timing-measured-on-the-emulator-not-derived-from-source).
The examples below use `PD6` — Arduino Uno pin `D6`.

Connect:

- strip `DIN` to the data pin, through the strip manufacturer's recommended series
  resistor if it specifies one (typically 300-500 ohm) — this protects the first LED
  from voltage spikes and is not something PyMCU can do in software
- strip `GND` to board `GND`
- strip `5V` to a supply that can source the strip's peak current (each WS2812 pixel
  can draw up to ~60 mA at full white; a board's own 5V regulator is usually not rated
  for more than a handful of pixels)

A large strip needs its own 5V supply, sharing ground with the board. This is a
hardware constraint of the LEDs, not something the library manages.

## Build the example

```bash
git clone https://github.com/PyMCU/pymcu-lib-neopixel
cd pymcu-lib-neopixel/examples/basic
pymcu build
```

`examples/basic` is the native API: it alternates the whole strip between dim red and
dim green every half second. Building it for an Arduino Uno produces:

```
Flash: 924 / 32768 bytes (2% of program storage)
       820 bytes of your code + 104 bytes of interrupt vector table
```

Flash the result the usual way for your board (`pymcu flash`, or whatever programmer
your board uses).

## Every example in the library

Each one is a complete, independent PyMCU project under
`examples/`. Build any of them the same way: `cd` into its
directory and run `pymcu build`. Figures below are for an ATmega328P (Arduino Uno) at
16 MHz, program storage 32768 bytes; `code` excludes the 104-byte interrupt vector
table every AVR program carries.

| Example | API layer | What it shows | Flash (code + vectors) |
|---|---|---|---|
| `basic` | native | Whole-strip `fill()` + `show()`, alternating colors | 820 + 104 = 924 B |
| `micropython_basic` | MicroPython-compatible | The same alternating fill, as `np.fill(...)` / `np.write()` | 822 + 104 = 926 B |
| `circuitpython_basic` | CircuitPython-compatible | The same alternating fill, as `pixels.fill(...)` with `auto_write` on | 820 + 104 = 924 B |
| `color_wipe` | native | A single pixel chasing down the strip — per-pixel `strip[i] = (r, g, b)`, not `fill()` | 744 + 104 = 848 B |
| `auto_write` | CircuitPython-compatible | Per-pixel writes with `auto_write` on: each `pixels[i] = ...` latches immediately, no `show()` calls anywhere in the file | 814 + 104 = 918 B |

Every figure above grew by 108 bytes from the library's first published version — a
bit-timing fix, not new functionality. Every example here only ever links one of
`_ws2812_b` (`PORTB` pins) or `_ws2812_d` (`PORTD` pins), whichever the pin you chose
needs; all five use `PD6`, so all five link `_ws2812_d` and its six `PORTD` cases
(`PD2`-`PD7`). Checking the compiled output confirms where the 108 bytes went: 48
`asm("NOP")` instructions (8 per pin case x 6 cases, 2 bytes each = 96 bytes) plus one
extra `RJMP` per case (2 bytes x 6 = 12 bytes) that the restructured branch needed to
skip the 0-bit path's NOPs on the 1-bit path. See
[How it works: bit timing](How-it-works.md#bit-timing-measured-on-the-emulator-not-derived-from-source)
for why the padding was needed. Every example above still comes in well under 1 KB.

`basic`, `micropython_basic` and `circuitpython_basic` run the identical visible
program (dim red, dim green, repeat) through each of the three APIs, so you can read
them side by side — see [The three APIs](The-three-APIs.md).

`color_wipe` and `auto_write` both go beyond `fill()`: they address individual pixels
every frame. Read them together to see what `auto_write` actually buys you — see
[How it works](How-it-works.md#auto_write).

Two of the five examples (`circuitpython_basic` and `auto_write`) print a build
warning worth knowing about before you rely on them as a reference for this library's
own CircuitPython code — see the note in
[The three APIs](The-three-APIs.md#a-note-on-the-circuitpython-examples).
