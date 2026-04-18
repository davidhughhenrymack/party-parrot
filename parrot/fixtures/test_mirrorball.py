"""Tests for Mirrorball fixture."""

from parrot.fixtures.mirrorball import Mirrorball


def test_mirrorball_dmx_dimmer_only() -> None:
    mb = Mirrorball(10)
    mb.set_dimmer(200)
    assert mb.values[0] == 200
    assert mb.get_dimmer() == 200
