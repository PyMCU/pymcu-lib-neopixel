# The CircuitPython neopixel API on the same pin and strip as examples/basic,
# so the two can be compared byte-for-byte. auto_write defaults to on, so
# fill() alone pushes the new colors out -- no separate show() call.
import board
import neopixel
from pymcu.time import delay_ms


def main():
    pixels = neopixel.NeoPixel(board.D6, 8)
    while True:
        pixels.fill((32, 0, 0))
        delay_ms(500)
        pixels.fill((0, 32, 0))
        delay_ms(500)
