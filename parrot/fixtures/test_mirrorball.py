"""Tests for Mirrorball fixture."""

from parrot.fixtures.mirrorball import Mirrorball
from parrot.utils.colour import Color


def test_mirrorball_dmx_layout_dimmer_rgb() -> None:
    mb = Mirrorball(10)
    assert mb.width == 4
    mb.set_dimmer(200)
    mb.set_color(Color("red"))
    assert mb.values[0] == 200
    assert mb.values[1] == 255
    assert mb.values[2] == 0
    assert mb.values[3] == 0
    assert mb.get_dimmer() == 200
    assert mb.get_color().red == 1.0


def test_mirrorball_set_color_mixes_channels() -> None:
    mb = Mirrorball(5)
    mb.set_color(Color(rgb=(0.4, 0.2, 1.0)))
    # colour.Color round-trips rgb values through HLS, so tolerate float drift.
    assert abs(mb.values[1] - 0.4 * 255) < 1e-6
    assert abs(mb.values[2] - 0.2 * 255) < 1e-6
    assert abs(mb.values[3] - 1.0 * 255) < 1e-6
