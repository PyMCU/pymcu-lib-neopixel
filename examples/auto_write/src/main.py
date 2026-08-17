# auto_write defaults to on: every pixels[i] = ... assignment below sends the
# whole strip immediately, so the wipe is visible one pixel at a time with no
# show() call anywhere in this file. Compare with color_wipe (the native API
# example), which sets a pixel and calls strip.show() itself once per frame --
# same wire bytes, but the caller decides when they go out.
import board
import neopixel
from pymcu.time import delay_ms
from pymcu.types import uint8


def main():
    pixels = neopixel.NeoPixel(board.D6, 8)
    while True:
        i: uint8 = 0
        while i < 8:
            pixels[i] = (0, 32, 0)
            delay_ms(80)
            i = i + 1
        i = 0
        while i < 8:
            pixels[i] = (0, 0, 0)
            delay_ms(80)
            i = i + 1
