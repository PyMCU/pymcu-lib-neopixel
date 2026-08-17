# Porting to a new architecture

Right now `pymcu.toml` declares `arch = ["avr"]`, and `_neopixel_core.py` raises a
compile-time `CompileError` for anything else:

```python
match __CHIP__.arch:
    case "avr":
        from _neopixel_avr import ws2812_init
        ws2812_init(pin)
    case _:
        raise CompileError("NeoPixel timing is only implemented for AVR")
```

That `raise` is deliberate: a compile error is the correct failure mode for a chip
this library doesn't support, because the alternative is compiling something that
looks like it works and produces the wrong signal on the wire.

## What a port needs to provide

`_neopixel_core.py` is the only file that knows what a chip is; every public API
(`neopixel.py` and both `compat/` adapters) is written against `Strip` and never
touches `__CHIP__` directly. A port to a new architecture means:

1. Add `_neopixel_<arch>.py`, mirroring `_neopixel_avr.py`'s three entry points:
   - `ws2812_init(pin: str)` — configure the pin as an output, held low.
   - `ws2812_write_byte(pin: str, val: uint8)` — bit-bang one byte, MSB first,
     WS2812 timing.
   - `ws2812_reset(pin: str)` — hold the pin low for the target's reset/latch
     duration (>50 us for WS2812/WS2812B; check your strip's datasheet, some clones
     want more).
2. Add one `case "<arch>":` branch per function in `_neopixel_core.py`, importing
   from the new module.
3. Add `"<arch>"` to `arch` in `pymcu.toml` under `[library.supports]`.

## Getting the bit timing right

This is the part that actually matters. A `match`/`if` tree with no explicit delay
does not reliably produce two pulse widths far enough apart for the strip to tell them
apart on its own — the branch instructions' cost depends on which path is taken and on
the target's code generation, neither of which you should infer from source-level
comments alone. The AVR implementation got exactly this wrong once (see
[How it works: bit timing](How-it-works.md#bit-timing-measured-on-the-emulator-not-derived-from-source)
for the account of what shipped, how it was found, and how it was fixed) before
`asm("NOP")` padding was added to both paths of `_ws2812_b` / `_ws2812_d`. Use that
as the template: get your bit-send loop compiling, then pad — don't assume comments
describing an intended cycle count are what the compiler actually produced.

Target windows to hit — the intersection of the WS2812 and WS2812B datasheets, which
is what this library's AVR driver targets and what `tests/test_timing.py` checks
against:

| | window |
|---|---|
| T0H (0-bit high pulse) | 250-500 ns |
| T1H (1-bit high pulse) | 650-850 ns |
| Reset (latch) | > 50 us low |

Aim for the middle of each window, not an edge — a real strip's actual tolerance may
be narrower than its datasheet's nominal numbers, and you have no margin to give up if
you're already sitting on the edge of the printed range. The AVR driver aims for
750 ns / 437.5 ns for exactly this reason.

To check a port, don't hand-count cycles from generated assembly (that's what went
wrong the first time on AVR) — measure it the way `tests/test_timing.py` does:
compile a probe program that sends a byte with every bit transition (`0xAA`) out a
pin, load the resulting `.hex` into a cycle-accurate emulator for your target if one
exists (this library uses `avr8sharp` for AVR), step it one cycle at a time, and record
how long the pin stays high between edges. That test file's `_pulse_widths()` helper is
AVR/`avr8sharp`-specific (it reads a `PORTD` GPIO through that emulator's API), but the
technique — probe byte, cycle-stepped emulator, measured pulse widths, assert against
the datasheet intersection — carries over directly to any target with a
cycle-accurate emulator available. Where no such emulator exists for your target,
the fallback is a real logic analyzer against real hardware; either way, verify the
result — a strip that lights up with plausible-looking colors is not the same as one
that reproduces the exact colors your code asked for, and WS2812 has no
error-detection to catch the difference for you.

## Pins

`ws2812_init`/`write_byte`/`reset` all `match pin:` against a fixed, explicit list of
port-string literals (`"PB0"`-`"PB5"`, `"PD2"`-`"PD7"` for AVR) rather than parsing the
string generically. This is what lets the compiler fold the whole dispatch away to one
branch per call site (see [How it works](How-it-works.md#pin-dispatch-two-different-mechanisms)) —
keep that pattern: list every valid pin explicitly, `raise CompileError(...)` in the
default case, and do not try to compute a port/bit pair from the string at compile
time unless you've confirmed the compiler folds that computation away too.

## Non-inline helpers

If your bit-send loop needs `asm()` labels (jump targets for a hand-written timing
loop), it cannot be `@inline` — an `@inline` function's body is duplicated at every
call site, and the assembler rejects a label defined more than once. `_ws2812_b` /
`_ws2812_d` in `_neopixel_avr.py` are the existing example of a non-inline helper
used for exactly this reason; see
[How it works](How-it-works.md#pin-dispatch-two-different-mechanisms) for what that
costs you: any argument to a non-inline function is a real runtime value in the
generated code, even when every call site happens to pass a compile-time constant.
