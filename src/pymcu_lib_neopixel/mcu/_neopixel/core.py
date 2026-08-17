# WS2812 / NeoPixel core -- the byte pump every API layer sits on.
#
# This is the only file in the library that knows what a chip is. The public
# modules -- neopixel.py and the compat adapters -- are written against this and
# stay free of architecture dispatch, so each one reads like the API it mirrors.
#
# Protocol: WS2812 GRB order, 1.25 us per bit, latch after >50 us low.
# Bit timing is cycle-exact, so interrupts must be off while a strip is being
# written. The callers own that decision; show() here only sends the latch.
from pymcu.chips import __CHIP__
from pymcu.exceptions import CompileError
from pymcu.types import uint8, inline


class Strip:
    """A pin driving a WS2812 chain, one byte at a time."""

    @inline
    def __init__(self, pin: str):
        self._pin = pin
        match __CHIP__.arch:
            case "avr":
                from _neopixel.avr import ws2812_init
                ws2812_init(pin)
            case _:
                # One string literal, not two adjacent ones: the parser reads a
                # single literal here and implicit concatenation is not part of
                # the accepted subset.
                raise CompileError("NeoPixel timing is only implemented for AVR")

    @inline
    def write_byte(self, value: uint8):
        match __CHIP__.arch:
            case "avr":
                from _neopixel.avr import ws2812_write_byte
                ws2812_write_byte(self._pin, value)
            case _:
                raise CompileError("NeoPixel timing is only implemented for AVR")

    @inline
    def latch(self):
        match __CHIP__.arch:
            case "avr":
                from _neopixel.avr import ws2812_reset
                ws2812_reset(self._pin)
            case _:
                raise CompileError("NeoPixel timing is only implemented for AVR")
