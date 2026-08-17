# How it works

## The WS2812 protocol, briefly

A WS2812 strip is a shift register with a latch: there is one data wire, no clock, and
each pixel reads and re-transmits the bytes meant for the pixels after it. You send
three bytes per pixel — green, red, blue, in that order on the wire, regardless of
which order your code addresses channels in — then hold the line low for a while so
the whole strip latches the new colors at once. Every 0 or 1 bit is encoded as one
pulse of a fixed total duration, split between a high phase and a low phase whose
relative lengths tell the strip which bit it received; there is no separate clock
signal, so the split has to be right.

`_neopixel/avr.py`'s header comment states the WS2812B target at 16 MHz this way:

```
0-bit: HIGH ~400 ns (6 cy), LOW ~850 ns (14 cy)
1-bit: HIGH ~800 ns (13 cy), LOW ~450 ns (7 cy)
Reset: hold LOW > 50 us
```

That is the intended encoding, and it is close to but not identical to what the driver
actually produces today (750 ns / 437.5 ns, chosen to sit inside the intersection of
the WS2812 and WS2812B datasheets rather than match either one's numbers exactly) —
see [Bit timing: measured on the emulator, not derived from source](#bit-timing-measured-on-the-emulator-not-derived-from-source)
below.

## The framebuffer

Every `NeoPixel` / `Strip` holds one array, `self._buf`, sized `n * 3` bytes for an
`n`-pixel strip — 3 bytes per pixel, GRB order, and nothing else. `__setitem__` and
`fill()` only ever write into this array; nothing goes to the wire until `show()` (or
`write()`, in the MicroPython adapter) is called, except when CircuitPython's
`auto_write` is on (see [`auto_write`](#auto_write) below).

The array is declared with a compile-time-sized annotation,
`self._buf: uint8[n * 3] = bytearray(n * 3)`. The annotation is what the compiler acts
on — it reserves a fixed block of SRAM, known at compile time because `n` is passed as
a literal at the call site and every constructor here is `@inline`. The
`bytearray(n * 3)` on the right is not allocated on the device at all; it exists only
so the same attribute is a real, indexable list under plain CPython, which is what
lets `tests/test_neopixel.py` run the framebuffer logic on a laptop without a compiler
in the loop (see `tests/conftest.py`).

Cost: a strip of 8 pixels is 24 bytes of SRAM. An ATmega328P has 2048 bytes of SRAM
total, shared with the stack and every other global; this library reserves nothing
beyond the one buffer per `NeoPixel` instance you construct.

## Why interrupts are disabled

`show()` wraps the whole byte stream in `asm("CLI")` / `asm("SEI")`:

```python
@inline
def show(self):
    asm("CLI")
    total: uint16 = self._n * 3
    i: uint16 = 0
    while i < total:
        self._strip.write_byte(self._buf[i])
        i = i + 1
    self._strip.latch()
    asm("SEI")
```

WS2812 bit timing is meant to be cycle-exact (see the numbers above) and has no
clock line to resynchronize against. An interrupt firing between two bits stalls the
data line at whatever level it happened to be at for the length of the ISR — typically
several hundred nanoseconds to microseconds — which the strip reads as either a
malformed bit or, if it stalls long enough, a premature latch. Every pixel from that
point in the byte stream onward comes out wrong. Disabling interrupts for the
transmission (a few hundred microseconds for a modest strip) is the whole mitigation;
there is no retry or checksum in the WS2812 protocol to fall back on.

## Pin dispatch: two different mechanisms

The library matches on pin names and bit indices in two places, and they are folded
very differently by the compiler — worth knowing if you're reading the generated
assembly or porting to a new chip.

`ws2812_init`, `ws2812_write_byte` and `ws2812_reset` in `_neopixel/avr.py` are all
`@inline` and take `pin: str`. Every caller in this library passes a string literal
(`"PD6"`, or a value that was itself inlined down to a literal from `NeoPixel("PD6",
8)`), so by the time the compiler reaches `match pin:` inside these functions, `pin`
is a compile-time constant and every non-matching `case` is dead code eliminated. None
of the twelve-way pin dispatch exists in the compiled output — only the one branch for
the pin you actually used.

`_ws2812_b` and `_ws2812_d` (the functions that actually bit-bang a byte to `PORTB` /
`PORTD`) are deliberately **not** `@inline` — the file's own comment explains why: an
`@inline` function containing asm labels would duplicate those labels at every call
site, and AVRA rejects duplicate labels. Being a real, non-inlined function means `bit`
arrives as a genuine runtime parameter in a register, even though every call site
passes a literal — constant folding does not cross a real function call. `match bit:`
inside them is therefore not eliminated: it compiles to a real chain of `CPI` /
`BRNE` comparisons, walked at runtime for every bit of every byte. You can see this in
any build's `dist/debug/firmware.asm` — for a strip on `PD6`, every single bit sent
runs through failed comparisons against `bit == 2`, `3`, `4`, `5` before reaching the
`bit == 6` case.

This dispatch overhead lengthens the *low* phase between bits (there's slack in the
WS2812 spec for that — the low phase just needs to be short enough that the strip
doesn't read it as a premature latch, and long enough to not blur into the next bit).
It is not the source of the high-phase timing that actually encodes each bit, covered
next.

## Bit timing: measured on the emulator, not derived from source

An earlier version of this page derived the high-phase pulse widths from the generated
assembly by hand-counting AVR cycles, and concluded (correctly, as it turned out) that
the driver did not separate a 0-bit from a 1-bit by enough margin to be read reliably.
That was fixed by padding both paths with `asm("NOP")` — six on the `b >= 128` (1-bit)
path, two on the `else` (0-bit) path — in eleven of the twelve pin cases across
`_ws2812_b` / `_ws2812_d`. This section reports what that fix actually produces,
measured rather than derived: `tests/test_timing.py` compiles a probe program that
sends the byte `0xAA` (`1010 1010` — every bit transition, both values) out `PD6`,
loads the resulting `firmware.hex` into the `avr8sharp` AVR emulator, steps the CPU one
cycle at a time, and records how many cycles the pin stays high and low between edges.
This is simulation, not an oscilloscope on a real strip — see the caveat further down.

**`PB0` is not one of the eleven.** `_ws2812_b`'s `case 0:` still has the original,
unpadded code (`pass` on the 1-bit path, no `asm("NOP")` anywhere). Probing `"PB0"` the
same way as `"PD6"` below measures **312.5 ns / 250 ns** — the original bug, confirmed
independently on the emulator, not carried over by assumption from the `PD6` numbers.
Every example in this library uses `PD6`, so nothing built here is affected, but
`PB0` (Arduino D8) is currently the one pin among the twelve this driver claims to
support where the timing is still wrong. If you need `PB0`, use a different pin until
this is fixed, or fix `case 0:` yourself to match `case 1:`'s six-NOP/two-NOP pattern.

For `case 6:` (`PD6`) inside `_ws2812_d`, the source is now:

```python
PORTD[6] = 1
if b >= 128:
    asm("NOP"); asm("NOP"); asm("NOP")
    asm("NOP"); asm("NOP"); asm("NOP")
else:
    asm("NOP"); asm("NOP")
    PORTD[6] = 0
PORTD[6] = 0
```

Measured on the emulator, sending `0xAA` on `PD6`:

| | high pulse | cycles | WS2812 / WS2812B window |
|---|---|---|---|
| 1-bit (T1H) | **750 ns** | 12 | 650-850 ns (both datasheets) |
| 0-bit (T0H) | **437.5 ns** | 7 | 250-500 ns (both datasheets) |

Twelve and seven cycles respectively — six NOPs plus the surrounding `SBI`/branch/`CBI`
overhead for the one path, two NOPs plus overhead for the other. Six NOPs (not eight)
was a deliberate choice: eight would put T1H at 875 ns, past the 850 ns ceiling of the
original WS2812 datasheet, while 750 ns sits inside both the WS2812 and WS2812B
windows, and 437.5 ns for T0H likewise sits inside both. The low phase between bits
(inter-bit gap, driven by the `match`/loop overhead described above, not by any NOP
padding) measured 2062.5-2125 ns (33-34 cycles) — comfortably under the ~50 us reset
threshold, so no bit's low phase risks latching the frame early. The resulting bit
period is roughly 2.5-2.9 us, well above the WS2812 datasheet's nominal 1.25 us; that
has no effect on correctness (WS2812 has no clock, only the reset threshold matters
for framing), but it does mean a long strip refreshes more slowly than the datasheet's
minimum period would suggest — worth knowing if you're timing an animation against a
target frame rate.

`tests/test_timing.py` asserts T0H and T1H both fall inside the intersection of the
WS2812 and WS2812B windows above, that a probe byte with both bit values in it produces
exactly two distinct pulse widths (catching the original bug directly — the shipped
version before this fix produced only one), that no inter-bit low is long enough to
latch the frame, and that all eight bits of the probe byte actually appear. It is
skipped (not failed) on a machine without `avr8sharp` or a `pymcu` compiler on `PATH`.

**What this does and doesn't confirm.** The numbers above come from stepping a
cycle-accurate AVR emulator against the exact compiled instruction stream, which is
precise about what the ATmega328P core will do — but it is still simulation. Rise/fall
times, the specific WS2812 clone's actual tolerance, and the physical pin's real
electrical behavior are not modeled. This has not been checked against a real strip on
a logic analyzer or oscilloscope as part of this documentation pass. Fixed timing
numbers landed at 750 ns / 437.5 ns specifically because that sits well inside the
published windows with margin either side, which is the right way to make an untested
physical claim safer, not a substitute for testing on real hardware before shipping
something timing-critical.

The same driver, patched identically, also ships as `pymcu`'s own built-in driver at
`pymcu.drivers.neopixel` (used by the CircuitPython layer's built-in `neopixel` module
— see [The three APIs](The-three-APIs.md#a-note-on-the-circuitpython-examples)), so
this fix applies to both copies.

## `auto_write`

Only the CircuitPython-compatible API has `auto_write`, matching upstream
CircuitPython. It is a plain instance field checked at the end of `__setitem__` and
`fill()`:

```python
@inline
def __setitem__(self, index, color):
    base: uint16 = index * 3
    self._buf[base + 0] = color[1]
    self._buf[base + 1] = color[0]
    self._buf[base + 2] = color[2]
    if self._auto_write:
        self.show()
```

With `auto_write` on (the default), every single pixel write re-streams the *entire*
strip — not just the one pixel that changed, because the WS2812 protocol has no way to
address a single pixel; the whole chain has to be re-clocked every time. Compare
`examples/color_wipe` (native API, `auto_write` does not exist — the caller decides
when to call `show()`, and calls it once per animation frame after moving the lit
pixel) with `examples/auto_write` (CircuitPython API, `auto_write` on — the same
one-pixel-at-a-time animation, but every `pixels[i] = ...` call is itself a full
`show()`). Both produce the same bytes on the wire per frame; the CircuitPython
version just costs a `show()` per pixel instead of one per frame, which matters if
you're writing many pixels in a tight loop and only care about the final state —
turning `auto_write` off and calling `show()` once avoids the redundant retransmissions.

## Brightness and `pixel_order`

The CircuitPython adapter accepts `brightness` and `pixel_order` constructor
arguments, for signature compatibility with upstream CircuitPython scripts, but
`pixels.brightness` always reads back `1.0` and `pixel_order` is not applied. Scaling
every channel of every pixel by a brightness factor would add a multiply to the
timing-critical byte loop in `show()`, and the framebuffer already stores colors in
fixed GRB wire order — there is no way to reorder channels without either storing
colors in a different in-memory order (which the wire format does not allow, since
WS2812 pixels expect GRB regardless of what the framebuffer layout looks like) or
adding a permutation step to every write. Both were left out rather than implemented
and silently wrong for the default color order.
