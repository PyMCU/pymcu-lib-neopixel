"""
The three APIs over one strip.

Each layer is tested against the idioms of the API it mirrors, because that is
the promise: a MicroPython script and a CircuitPython script both run here
unchanged. The framebuffer is always WS2812 wire order (GRB), so red is the
byte triple (0, 255, 0) on the wire -- the assertion that catches a channel
swap in any of the three.
"""

import importlib
import sys

import pytest


def _load(module_path: str, name: str):
    """Import one of the layer modules by file, since all three are `neopixel`."""
    from pathlib import Path

    root = Path(__file__).resolve().parents[1] / "src" / "pymcu_lib_neopixel" / "mcu"
    spec = importlib.util.spec_from_file_location(name, root / module_path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


@pytest.fixture
def native():
    return _load("neopixel.py", "native_neopixel")


@pytest.fixture
def micropython():
    return _load("compat/micropython/neopixel.py", "mp_neopixel")


@pytest.fixture
def circuitpython():
    return _load("compat/circuitpython/neopixel.py", "cp_neopixel")


class _Pin:
    """What machine.Pin looks like from the outside: a name the HAL understands."""

    def __init__(self, name):
        self._name = name


# ---------------------------------------------------------------------------
# Native API
# ---------------------------------------------------------------------------

class TestNative:
    def test_length_and_pin(self, native):
        strip = native.NeoPixel("PD6", 8)
        assert len(strip) == 8
        assert strip._strip.pin == "PD6"

    def test_fill_is_grb_on_the_wire(self, native):
        strip = native.NeoPixel("PD6", 3)
        strip.fill((255, 0, 0))
        assert list(strip._buf) == [0, 255, 0] * 3

    def test_setitem_touches_one_pixel(self, native):
        strip = native.NeoPixel("PD6", 4)
        strip[2] = (10, 20, 30)
        assert list(strip._buf[6:9]) == [20, 10, 30]
        assert list(strip._buf[0:6]) == [0] * 6

    def test_show_sends_every_byte_then_latches(self, native):
        strip = native.NeoPixel("PD6", 2)
        strip.fill((1, 2, 3))
        strip.show()
        assert strip._strip.sent == [2, 1, 3, 2, 1, 3]
        assert strip._strip.latched == 1


# ---------------------------------------------------------------------------
# MicroPython API -- a MicroPython script must run unchanged
# ---------------------------------------------------------------------------

class TestMicroPython:
    def test_takes_a_machine_pin(self, micropython):
        np = micropython.NeoPixel(_Pin("PD6"), 8)
        assert np._strip.pin == "PD6"
        assert len(np) == 8

    def test_setitem_then_write(self, micropython):
        np = micropython.NeoPixel(_Pin("PD6"), 2)
        np[0] = (255, 0, 0)
        np[1] = (0, 0, 255)
        assert np._strip.sent == []      # nothing goes out before write()
        np.write()
        assert np._strip.sent == [0, 255, 0, 0, 0, 255]
        assert np._strip.latched == 1

    def test_fill(self, micropython):
        np = micropython.NeoPixel(_Pin("PD6"), 3)
        np.fill((0, 64, 0))
        assert list(np._buf) == [64, 0, 0] * 3


# ---------------------------------------------------------------------------
# CircuitPython API -- a CircuitPython script must run unchanged
# ---------------------------------------------------------------------------

class TestCircuitPython:
    def test_construct_and_len(self, circuitpython):
        pixels = circuitpython.NeoPixel("PD6", 8)
        assert len(pixels) == 8
        assert pixels.n == 8

    def test_auto_write_latches_immediately(self, circuitpython):
        pixels = circuitpython.NeoPixel("PD6", 1)
        assert pixels.auto_write == 1
        pixels[0] = (255, 0, 0)
        assert pixels._strip.sent == [0, 255, 0]

    def test_auto_write_off_defers_to_show(self, circuitpython):
        pixels = circuitpython.NeoPixel("PD6", 1, auto_write=0)
        pixels[0] = (255, 0, 0)
        assert pixels._strip.sent == []
        pixels.show()
        assert pixels._strip.sent == [0, 255, 0]

    def test_fill_tuple_is_grb(self, circuitpython):
        pixels = circuitpython.NeoPixel("PD6", 3, auto_write=0)
        pixels.fill((255, 0, 0))
        assert list(pixels._buf) == [0, 255, 0] * 3

    def test_colour_order_constants(self, circuitpython):
        assert circuitpython.GRB == "GRB"
        assert circuitpython.RGB == "RGB"

    def test_deinit_is_harmless(self, circuitpython):
        circuitpython.NeoPixel("PD6", 1).deinit()


# ---------------------------------------------------------------------------
# Cross-layer
# ---------------------------------------------------------------------------

def test_every_layer_puts_the_same_bytes_on_the_wire(native, micropython, circuitpython):
    """One strip, three APIs: the wire does not care which one you wrote."""
    a = native.NeoPixel("PD6", 2)
    a.fill((10, 20, 30))
    a.show()

    b = micropython.NeoPixel(_Pin("PD6"), 2)
    b.fill((10, 20, 30))
    b.write()

    c = circuitpython.NeoPixel("PD6", 2, auto_write=0)
    c.fill((10, 20, 30))
    c.show()

    assert a._strip.sent == b._strip.sent == c._strip.sent
