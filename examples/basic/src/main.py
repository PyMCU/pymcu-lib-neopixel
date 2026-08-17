from neopixel import NeoPixel
from pymcu.time import delay_ms


def main():
    strip = NeoPixel("PD6", 8)
    while True:
        strip.fill((32, 0, 0))
        strip.show()
        delay_ms(500)
        strip.fill((0, 32, 0))
        strip.show()
        delay_ms(500)
