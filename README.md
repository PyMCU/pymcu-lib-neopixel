# pymcu-lib-neopixel

WS2812 / NeoPixel addressable LED strips for [PyMCU](https://pymcu.org) — compiled
to native machine code, with no interpreter on the chip.

```bash
pymcu install neopixel
```

## The same strip, three APIs

Which one you get depends on the `stdlib` layer your project declares. The import is
always `neopixel`.

**Native** (`stdlib` unset):

```python
from neopixel import NeoPixel

strip = NeoPixel("PD6", 8)
strip[0] = (255, 0, 0)
strip.show()
```

**MicroPython** (`stdlib = ["micropython"]`) — a MicroPython script, unchanged:

```python
from machine import Pin
from neopixel import NeoPixel

np = NeoPixel(Pin(6), 8)
np[0] = (255, 0, 0)
np.write()
```

**CircuitPython** (`stdlib = ["circuitpython"]`) — a CircuitPython script, unchanged:

```python
import board
import neopixel

pixels = neopixel.NeoPixel(board.D6, 8, auto_write=False)
pixels.fill((0, 32, 0))
pixels.show()
```

None of those three files contains a single conditional: the layer adapters are plain
Python written against each API as it is documented upstream. Everything that has to
know about a chip lives in one private module, `_neopixel_core`, and the compiler folds
it away.

## Cost

Colours live in a per-strip SRAM framebuffer, 3 bytes per pixel in WS2812 wire order —
24 bytes for a strip of 8, and nothing else. Every method is `@inline`, so no object is
allocated on the device and no method call survives compilation.

Measured figures per chip are published in the
[library index](https://libraries.pymcu.org/index.json).

## Supported hardware

WS2812 / WS2812B / NeoPixel strips on **AVR** (ATmega328P and friends) at 16 MHz.
Bit timing is cycle-exact, so `show()` / `write()` disables interrupts for the duration
of the transmission and restores them afterwards.

Other architectures raise a compile-time error rather than returning something that
looks like it worked. Ports are welcome: `_neopixel_avr.py` is the whole contract.

## License

MIT.
