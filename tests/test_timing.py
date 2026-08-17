"""
The bit timing, measured on the emulator rather than argued about.

WS2812 has no clock line: a bit is a one or a zero purely by how long the line
stays high. The first version of this driver produced 312 ns for a one and
250 ns for a zero -- both inside the zero window -- so a strip read every bit as
zero and stayed dark. Nothing in the source said so, and the flash figure was
perfectly healthy.

So the check is the thing itself: compile a byte with alternating bits, step the
emulated CPU one cycle at a time, and measure how long the pin is actually high.

Every supported pin is measured, not one of them. The fix for that first bug
missed PB0 -- its source had a comment where the others did not -- and a test
that only probed PD6 called the driver healthy while one pin still sent every
bit as a zero. Twelve pins, twelve measurements.

Skipped when avr8sharp or a compiler is not available, which keeps `pytest`
useful on a machine with neither.
"""

import shutil
import subprocess
import sys
from pathlib import Path

import pytest

CYCLE_NS = 1000.0 / 16.0        # 16 MHz
PROBE_BYTE = 0xAA               # 1010 1010: both bit values, every transition

# WS2812 and WS2812B disagree slightly; a driver worth shipping is inside both.
T0H_NS = (250, 500)
T1H_NS = (650, 850)
RESET_NS = 50_000               # a low longer than this latches the frame

# (pin name, GPIO index the emulator uses for its port, bit within the port)
PORT_B, PORT_D = 0, 2
PINS = [
    ("PB0", PORT_B, 0), ("PB1", PORT_B, 1), ("PB2", PORT_B, 2),
    ("PB3", PORT_B, 3), ("PB4", PORT_B, 4), ("PB5", PORT_B, 5),
    ("PD2", PORT_D, 2), ("PD3", PORT_D, 3), ("PD4", PORT_D, 4),
    ("PD5", PORT_D, 5), ("PD6", PORT_D, 6), ("PD7", PORT_D, 7),
]

PROBE = """\
from _neopixel.avr import ws2812_init, ws2812_write_byte
from pymcu.types import asm


def main():
    ws2812_init("{pin}")
    asm("CLI")
    ws2812_write_byte("{pin}", 0xAA)
    asm("SEI")
    while True:
        pass
"""

PROJECT = """\
[project]
name = "ws2812-timing-probe"
version = "0.1.0"
dependencies = []

[tool.pymcu]
target = "atmega328p"
frequency = 16000000
sources = "src"
entry = "main.py"
"""


def _measure(hex_text: str, port_index: int, bit: int) -> tuple[list[int], list[int]]:
    """Return (high, low) run lengths in cycles, by stepping one cycle at a time."""
    from avr8sharp import Simulation

    sim = Simulation.create().with_frequency(16_000_000).with_hex(hex_text)
    port = sim.add_gpio(port_index)

    highs, lows, high_since, low_since, previous = [], [], None, None, False
    for _ in range(20_000):
        sim.run_cycles(1)
        now = port.pin_high(bit)
        if now and not previous:
            high_since = sim.cpu.cycles
            if low_since is not None:
                lows.append(sim.cpu.cycles - low_since)
        elif previous and not now and high_since is not None:
            highs.append(sim.cpu.cycles - high_since)
            low_since = sim.cpu.cycles
        previous = now
    return highs, lows


def _pymcu() -> str | None:
    """
    Prefer the pymcu that lives beside the interpreter running this test.

    A `pymcu` earlier on PATH -- a globally installed one, say -- builds
    against a different environment than the editable install under test, and
    reports this library as missing when it is merely somewhere else. The venv
    running pytest is the one it was installed into, so its bin/ is trusted
    first; a bare `shutil.which` remains the fallback outside a venv layout.
    """
    beside_interpreter = Path(sys.executable).parent / "pymcu"
    if beside_interpreter.exists():
        return str(beside_interpreter)
    return shutil.which("pymcu")


@pytest.fixture(scope="module")
def probe(tmp_path_factory):
    """Builds a probe per pin, once, and hands back its measurements."""
    pytest.importorskip("avr8sharp", reason="needs the emulator")
    pymcu = _pymcu()
    if pymcu is None:
        pytest.skip("needs a pymcu compiler on PATH")

    measured: dict[str, tuple[list[int], list[int]]] = {}
    for pin, port_index, bit in PINS:
        project = tmp_path_factory.mktemp(f"probe_{pin}")
        (project / "src").mkdir()
        (project / "pyproject.toml").write_text(PROJECT)
        (project / "src" / "main.py").write_text(PROBE.format(pin=pin))

        build = subprocess.run([pymcu, "build"], cwd=project, capture_output=True, text=True)
        # A missing compiler is a skip; a compiler that refuses this driver is a
        # failure. Treating the second as a skip is how a broken library passes
        # its own test suite in silence -- the first draft of this file did
        # exactly that, and swallowed a pin that did not compile.
        if build.returncode != 0:
            output = (build.stdout + build.stderr).strip().splitlines()
            pytest.fail(f"the probe for {pin} did not build:\n"
                        + "\n".join(output[-6:]))

        firmware = project / "dist" / "firmware.hex"
        if not firmware.exists():
            pytest.fail(f"no firmware.hex produced for {pin}")

        measured[pin] = _measure(firmware.read_text(), port_index, bit)
    return measured


@pytest.mark.parametrize("pin", [name for name, _port, _bit in PINS])
class TestBitTiming:
    def test_a_one_and_a_zero_are_different_pulses(self, probe, pin):
        """The failure that shipped: both bit values the same width."""
        highs, _lows = probe[pin]
        assert len(set(highs)) == 2, (
            f"{pin}: expected two distinct pulse widths, got {sorted(set(highs))} "
            "cycles -- a strip cannot tell these bits apart"
        )

    def test_the_zero_pulse_is_in_spec(self, probe, pin):
        highs, _lows = probe[pin]
        zero_ns = min(set(highs)) * CYCLE_NS
        assert T0H_NS[0] <= zero_ns <= T0H_NS[1], f"{pin}: T0H = {zero_ns:.0f} ns"

    def test_the_one_pulse_is_in_spec(self, probe, pin):
        highs, _lows = probe[pin]
        one_ns = max(set(highs)) * CYCLE_NS
        assert T1H_NS[0] <= one_ns <= T1H_NS[1], f"{pin}: T1H = {one_ns:.0f} ns"

    def test_no_gap_long_enough_to_latch_the_frame(self, probe, pin):
        """A low longer than the reset window ends the frame halfway through it."""
        _highs, lows = probe[pin]
        longest_ns = max(lows) * CYCLE_NS if lows else 0
        assert longest_ns < RESET_NS, f"{pin}: inter-bit low of {longest_ns:.0f} ns"

    def test_all_eight_bits_are_sent(self, probe, pin):
        highs, _lows = probe[pin]
        assert len(highs) == 8, f"{pin}: 0xAA should produce 8 pulses, got {len(highs)}"
