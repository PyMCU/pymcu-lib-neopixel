"""
What an RP2040 or RP2350 needs from the library beyond the framebuffer.

The WS2812 waveform is made by a PIO state machine there (pymcu.hal.ws2812), so the library
only has to say so: the manifest has to name the architecture, or the driver skips the library
("Skipping library neopixel: supports avr"), and a frame has to be bracketed by begin_frame and
end_frame so that the AVR's interrupt masking lives in the core and not in the three API layers.
The compiled result is measured in the emulator by pymcu-arm (CpNeopixelWriteTests,
Ws2812PioTests) and by building the Adafruit simpletest for the Feather RP2040.
"""

import importlib.util
import sys
import tomllib
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1] / "src" / "pymcu_lib_neopixel"


def _load(module_path: str, name: str):
    spec = importlib.util.spec_from_file_location(name, ROOT / "mcu" / module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def test_the_manifest_supports_the_arm_parts():
    manifest = tomllib.loads((ROOT / "pymcu.toml").read_text())

    assert manifest["library"]["supports"]["arch"] == ["avr", "arm"]


def test_every_layer_brackets_a_frame_in_the_core():
    class MachinePin:
        _name = "PD6"

    for path, name, pin, send in [("neopixel.py", "native", "PD6", "show"),
                                  ("compat/circuitpython/neopixel.py", "cp", "PD6", "show"),
                                  ("compat/micropython/neopixel.py", "mp", MachinePin(), "write")]:
        module = _load(path, f"arm_{name}")
        strip = module.NeoPixel(pin, 2)
        getattr(strip, send)()

        assert strip._strip.events == ["begin", "bytes", "latch", "end"], name


def test_no_layer_masks_interrupts_itself():
    for path in ["neopixel.py", "compat/circuitpython/neopixel.py", "compat/micropython/neopixel.py"]:
        source = (ROOT / "mcu" / path).read_text()

        assert 'asm("CLI")' not in source and 'asm("SEI")' not in source, path


def test_the_core_masks_interrupts_only_on_an_avr():
    source = (ROOT / "mcu" / "_neopixel" / "core.py").read_text()
    begin = source[source.index("def begin_frame"):source.index("def end_frame")]

    assert 'case "avr":' in begin and 'asm("CLI")' in begin and "case _:" in begin
