# CircuitPython-compatible neopixel module.
#
# The code below is the CircuitPython API, unchanged:
#
#   import board
#   import neopixel
#
#   pixels = neopixel.NeoPixel(board.D6, 8, auto_write=False)
#   pixels[0] = (255, 0, 0)
#   pixels.fill((0, 0, 0))
#   pixels.show()
#
# Same script, no interpreter: every call below is expanded at compile time into
# the WS2812 bit-banging routine, and the strip's colours are the only thing
# that exists in SRAM.
from pymcu.types import asm, inline, uint8, uint16

from _neopixel_core import Strip

# Colour orders, named as CircuitPython names them.
RGB = "RGB"
GRB = "GRB"
RGBW = "RGBW"
GRBW = "GRBW"


class NeoPixel:
    """A sequence of WS2812 pixels, addressed like a list."""

    @inline
    def __init__(self, pin, n: uint8, bpp: uint8 = 3, brightness: float = 1.0,
                 auto_write: uint8 = 1, pixel_order=None):
        self._strip = Strip(pin)
        self._n = n
        self._auto_write = auto_write
        self._buf: uint8[n * 3] = bytearray(n * 3)

    @inline
    def __len__(self) -> uint8:
        return self._n

    @property
    def n(self) -> uint8:
        return self._n

    @property
    def auto_write(self) -> uint8:
        return self._auto_write

    @property
    def brightness(self) -> float:
        # Reported for API compatibility. Scaling every channel on the way out
        # would cost a multiply per byte inside the timing-critical loop, and
        # the strip has no brightness of its own to read back.
        return 1.0

    @inline
    def __setitem__(self, index, color):
        base: uint16 = index * 3
        self._buf[base + 0] = color[1]   # G
        self._buf[base + 1] = color[0]   # R
        self._buf[base + 2] = color[2]   # B
        if self._auto_write:
            self.show()

    @inline
    def fill(self, color):
        g: uint8 = color[1]
        r: uint8 = color[0]
        b: uint8 = color[2]
        i: uint8 = 0
        while i < self._n:
            base: uint16 = i * 3
            self._buf[base + 0] = g
            self._buf[base + 1] = r
            self._buf[base + 2] = b
            i = i + 1
        if self._auto_write:
            self.show()

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

    @inline
    def deinit(self):
        pass
