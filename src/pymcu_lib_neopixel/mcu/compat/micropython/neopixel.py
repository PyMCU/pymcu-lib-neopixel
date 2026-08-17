# MicroPython-compatible neopixel module.
#
# The code below is the MicroPython API, unchanged:
#
#   from machine import Pin
#   from neopixel import NeoPixel
#
#   np = NeoPixel(Pin(6), 8)
#   np[0] = (255, 0, 0)
#   np.fill((0, 0, 0))
#   np.write()
#
# Same script, no interpreter: `np.write()` expands into the WS2812 bit-banging
# routine at compile time, and the pixel buffer is the only thing that exists in
# SRAM.
from pymcu.types import asm, inline, uint8, uint16

from _neopixel.core import Strip


class NeoPixel:
    """A WS2812 chain driven from a machine.Pin, addressed like a list."""

    @inline
    def __init__(self, pin, n: uint8, bpp: uint8 = 3, timing: uint8 = 1):
        # machine.Pin carries the port name the HAL works in; taking it here is
        # what lets a MicroPython script hand us its own Pin object.
        self._strip = Strip(pin._name)
        self._n = n
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
    def write(self):
        # WS2812 bit timing is cycle-exact: an interrupt mid-byte corrupts every
        # pixel after it.
        asm("CLI")
        total: uint16 = self._n * 3
        i: uint16 = 0
        while i < total:
            self._strip.write_byte(self._buf[i])
            i = i + 1
        self._strip.latch()
        asm("SEI")
