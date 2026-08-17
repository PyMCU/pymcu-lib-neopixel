# NeoPixel (WS2812/WS2812B) strips -- native PyMCU API.
#
#   from neopixel import NeoPixel
#
#   strip = NeoPixel("PD6", 8)
#   strip[0] = (255, 0, 0)
#   strip.show()
#
# Colours are held in a per-strip SRAM framebuffer, three bytes per pixel in
# WS2812 wire (GRB) order, so a single pixel can be changed without rewriting
# the rest. A strip of 8 costs 24 bytes of SRAM and nothing else: every method
# is @inline and no object exists on the device.
from pymcu.types import asm, inline, uint8, uint16

from _neopixel.core import Strip


class NeoPixel:

    @inline
    def __init__(self, pin: str, n: uint8):
        self._strip = Strip(pin)
        self._n = n
        # The annotation reserves a fixed uint8[n*3] array; the bytearray()
        # initialiser is what makes the same attribute indexable under CPython
        # simulation.
        self._buf: uint8[n * 3] = bytearray(n * 3)

    @inline
    def __len__(self) -> uint8:
        return self._n

    @inline
    def __setitem__(self, index, color):
        base: uint16 = index * 3
        self._buf[base + 0] = color[1]   # G
        self._buf[base + 1] = color[0]   # R
        self._buf[base + 2] = color[2]   # B

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

    @inline
    def show(self):
        # WS2812 bit timing is cycle-exact: an interrupt in the middle of a
        # byte corrupts the colours of every pixel after it.
        asm("CLI")
        total: uint16 = self._n * 3
        i: uint16 = 0
        while i < total:
            self._strip.write_byte(self._buf[i])
            i = i + 1
        self._strip.latch()
        asm("SEI")
