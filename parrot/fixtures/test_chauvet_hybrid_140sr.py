"""Tests for Chauvet Intimidator Hybrid 140SR DMX mapping."""

from parrot.fixtures.chauvet.intimidator_hybrid_140sr import (
    ChauvetIntimidatorHybrid140SR_13Ch,
    ChauvetIntimidatorHybrid140SR_19Ch,
)


def test_hybrid_140sr_19ch_width_and_dimmer_channel():
    m = ChauvetIntimidatorHybrid140SR_19Ch(1)
    assert m.width == 19
    assert len(m.values) == 19
    m.set_dimmer(255)
    assert m.values[15] == 255


def test_hybrid_140sr_13ch_width_no_dimmer_channel():
    m = ChauvetIntimidatorHybrid140SR_13Ch(1)
    assert m.width == 13
    assert len(m.values) == 13
    assert "dimmer" not in m.dmx_layout
