# A single pixel chases down the strip -- fill() alone cannot do this, since
# it sets every pixel to the same color. strip[pos] addresses one pixel at a
# time, and the previous one is cleared explicitly before the next is lit.
from neopixel import NeoPixel
from pymcu.time import delay_ms
from pymcu.types import uint8


def main():
    strip = NeoPixel("PD6", 8)
    pos: uint8 = 0
    while True:
        strip.fill((0, 0, 0))
        strip[pos] = (0, 0, 32)
        strip.show()
        delay_ms(120)
        pos = pos + 1
        if pos >= 8:
            pos = 0
