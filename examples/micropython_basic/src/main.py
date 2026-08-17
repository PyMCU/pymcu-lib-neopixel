# The MicroPython neopixel API on the same pin and strip as examples/basic,
# so the two can be compared byte-for-byte.
from machine import Pin
from neopixel import NeoPixel
from pymcu.time import delay_ms


def main():
    np = NeoPixel(Pin(6), 8)
    while True:
        np.fill((32, 0, 0))
        np.write()
        delay_ms(500)
        np.fill((0, 32, 0))
        np.write()
        delay_ms(500)
