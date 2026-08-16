"""
Enough of PyMCU to import the library under plain CPython.

The modules here target a microcontroller: `pymcu.types` annotations, the
`__CHIP__` constant and the WS2812 bit-banging all mean something only to the
compiler. Stubbing them lets the framebuffer logic -- the part that is ordinary
Python, and the part most likely to have an off-by-one -- be tested on a laptop.

What the compiler does with these files is verified separately, by compiling the
example for real.
"""

import sys
from pathlib import Path
from types import ModuleType

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src" / "pymcu_lib_neopixel"))


def _install_stubs() -> None:
    pymcu = ModuleType("pymcu")
    pymcu.__path__ = []
    sys.modules["pymcu"] = pymcu

    types_mod = ModuleType("pymcu.types")

    def _identity(f):
        return f

    class _Int:
        """Stands in for uint8/uint16: annotations only, never constructed."""

        def __class_getitem__(cls, item):
            return cls

    types_mod.inline = _identity
    types_mod.uint8 = _Int
    types_mod.uint16 = _Int
    types_mod.asm = lambda instruction: None
    sys.modules["pymcu.types"] = types_mod
    pymcu.types = types_mod

    chips = ModuleType("pymcu.chips")

    class _Chip(str):
        arch = "avr"
        name = "atmega328p"

    chips.__CHIP__ = _Chip("atmega328p")
    sys.modules["pymcu.chips"] = chips
    pymcu.chips = chips

    exceptions = ModuleType("pymcu.exceptions")

    class CompileError(Exception):
        pass

    exceptions.CompileError = CompileError
    sys.modules["pymcu.exceptions"] = exceptions
    pymcu.exceptions = exceptions

    # The core is the one module that talks to the hardware; under CPython it
    # records what it was told to send, which is what the tests assert on.
    core = ModuleType("_neopixel_core")

    class Strip:
        def __init__(self, pin):
            self.pin = pin
            self.sent = []
            self.latched = 0

        def write_byte(self, value):
            self.sent.append(value)

        def latch(self):
            self.latched += 1

    core.Strip = Strip
    sys.modules["_neopixel_core"] = core


_install_stubs()
