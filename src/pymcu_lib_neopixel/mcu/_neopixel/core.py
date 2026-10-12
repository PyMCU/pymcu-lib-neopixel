# WS2812 / NeoPixel core -- the byte pump every API layer sits on.
#
# This is the only file in the library that knows what a chip is. The public
# modules -- neopixel.py and the compat adapters -- are written against this and
# stay free of architecture dispatch, so each one reads like the API it mirrors.
#
# Protocol: WS2812 GRB order, 1.25 us per bit, latch after >50 us low.
# On an AVR the bit timing is counted instructions, so interrupts must be off while
# a strip is being written (begin_frame / end_frame); on an RP2040 or RP2350 a PIO
# state machine makes it, and they need not be. The callers own that decision; show() here only sends the latch.
from pymcu.chips import __CHIP__
from pymcu.exceptions import CompileError
from pymcu.types import uint8, inline, asm


class Strip:
    """A pin driving a WS2812 chain, one byte at a time."""

    @inline
    def __init__(self, pin: str):
        self._pin = pin
        match __CHIP__.arch:
            case "avr":
                from _neopixel.avr import ws2812_init
                ws2812_init(pin)
            case "arm":
                # RP2040 / RP2350: a PIO state machine makes the waveform (pymcu.hal.ws2812).
                # `pin` is the GPIO number there.
                from pymcu.hal.ws2812 import ws2812_init
                ws2812_init(pin)
            case _:
                # One string literal, not two adjacent ones: the parser reads a
                # single literal here and implicit concatenation is not part of
                # the accepted subset.
                raise CompileError("NeoPixel timing is only implemented for AVR, RP2040 and RP2350")

    @inline
    def write_byte(self, value: uint8):
        match __CHIP__.arch:
            case "avr":
                from _neopixel.avr import ws2812_write_byte
                ws2812_write_byte(self._pin, value)
            case "arm":
                from pymcu.hal.ws2812 import ws2812_write_byte
                ws2812_write_byte(self._pin, value)
            case _:
                raise CompileError("NeoPixel timing is only implemented for AVR, RP2040 and RP2350")

    @inline
    def latch(self):
        match __CHIP__.arch:
            case "avr":
                from _neopixel.avr import ws2812_reset
                ws2812_reset(self._pin)
            case "arm":
                from pymcu.hal.ws2812 import ws2812_reset
                ws2812_reset(self._pin)
            case _:
                raise CompileError("NeoPixel timing is only implemented for AVR, RP2040 and RP2350")

    @inline
    def begin_frame(self):
        """Called before the first byte of a frame."""
        match __CHIP__.arch:
            case "avr":
                # The bit times are counted instructions: an interrupt taken mid-byte
                # stretches one high time past its tolerance.
                asm("CLI")
            case _:
                # A PIO state machine keeps its own time.
                pass

    @inline
    def end_frame(self):
        """Called after the latch."""
        match __CHIP__.arch:
            case "avr":
                asm("SEI")
            case _:
                pass
