# The three APIs

`import neopixel` resolves differently depending on the `stdlib` layer your project
declares in `pyproject.toml`. All three give you a `NeoPixel` class over the same
per-strip SRAM framebuffer, and all three write GRB bytes to the wire through the same
`_neopixel_core.Strip` — see [How it works](How-it-works.md). The difference is only
which API you get, chosen to match a script you may already have.

## Native (`stdlib` unset)

```python
from neopixel import NeoPixel

strip = NeoPixel("PD6", 8)
strip.fill((32, 0, 0))
strip.show()
```

The pin is a plain PyMCU port string (`"PD6"`, `"PB5"`, ...), and nothing latches until
you call `show()`. This is the API to reach for in new PyMCU code: it has no
compatibility baggage and its two calls map directly onto what the hardware does
(fill the buffer, stream the buffer).

`__setitem__` is also available for single-pixel writes: `strip[0] = (255, 0, 0)`, then
`strip.show()` when you're ready to send it.

## MicroPython-compatible (`stdlib = ["micropython"]`)

```python
from machine import Pin
from neopixel import NeoPixel

np = NeoPixel(Pin(6), 8)
np[0] = (255, 0, 0)
np.fill((0, 0, 0))
np.write()
```

This is the MicroPython `neopixel.NeoPixel` API unchanged: construct from a
`machine.Pin`, address pixels with `[]`, call `write()` (not `show()`) to latch. The
adapter takes the `Pin` object apart (`pin._name`) to recover the port string the core
driver needs — MicroPython scripts never see that, they just pass a `Pin`.

`np.write()` never latches implicitly. If you only ever call `fill()` +`write()`, this
behaves exactly like the native API with different method names.

## CircuitPython-compatible (`stdlib = ["circuitpython"]`)

```python
import board
import neopixel

pixels = neopixel.NeoPixel(board.D6, 8, auto_write=False)
pixels.fill((0, 32, 0))
pixels.show()
```

This is the CircuitPython `neopixel.NeoPixel` API: construct from a `board.*` pin
constant, `auto_write` defaults to on (matching CircuitPython), and `pixels.n` /
`pixels.auto_write` / `pixels.brightness` are exposed as read-only properties for
scripts that inspect them. `pixels.brightness` always reads back `1.0` — see
[How it works](How-it-works.md#brightness-and-pixel_order) for why per-pixel scaling
is not implemented.

With `auto_write` on (the default), every `pixels[i] = ...` and every `fill(...)`
latches the strip immediately — see `examples/auto_write` and
[How it works](How-it-works.md#auto_write).

## A note on the CircuitPython examples

`board.D6` is a plain string constant (`"PD6"`), defined by the `circuitpython` stdlib
layer itself, not by this library — the same layer that provides `board`. That layer
also ships its own `neopixel` module
(`pymcu_circuitpython/neopixel.py`), and **the layer's module wins over the
library's**: the compiler puts compat-layer modules ahead of installed libraries on
the include path specifically so a library cannot shadow a name like `machine` or
`digitalio` out from under a script that expects the layer's own version. `neopixel`
happens to be a name both provide.

Building `examples/circuitpython_basic` or `examples/auto_write` prints:

```
Warning: 'neopixel' is provided by both the circuitpython layer and
pymcu-lib-neopixel; the layer wins, so the library's version is not being compiled
```

The two implementations are independent copies of the same API and (as far as this
library's driver goes — see [How it works](How-it-works.md)) the same underlying AVR
timing code, so the examples still build, run, and demonstrate the CircuitPython API
correctly. What they do *not* do is exercise
`src/pymcu_lib_neopixel/compat/circuitpython/neopixel.py` — that file is only reached
by a project that installs this library *without* also declaring the `circuitpython`
stdlib layer, which is not a combination the CLI offers a way to express today. In
practice this means the library's own CircuitPython adapter has no build in this repo
that actually compiles it; the `tests/test_neopixel.py` suite is what exercises its
logic (under stubbed, non-compiled Python), not any example. Worth knowing if you're
changing that file: a passing `pytest` run does not mean the compiler has ever seen it.
