"""Tests for Chauvet Intimidator Hybrid 140SR DMX mapping (``rogue_hybrid_rh1`` module)."""

from parrot.fixtures.chauvet.rogue_hybrid_rh1 import (
    ChauvetIntimidatorHybrid140SR_13Ch,
    ChauvetIntimidatorHybrid140SR_19Ch,
)


def test_hybrid_140sr_advertises_prism_and_focus():
    """Hybrid 140SR has both a 7-facet prism and a variable-focus optic; the
    rendering capability flags must stay True so desktop/web previews show
    the splay fan and narrowing beam when interpreters engage them."""
    m19 = ChauvetIntimidatorHybrid140SR_19Ch(1)
    m13 = ChauvetIntimidatorHybrid140SR_13Ch(1)
    assert m19.supports_prism is True
    assert m19.supports_focus is True
    assert m13.supports_prism is True
    assert m13.supports_focus is True


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


def test_hybrid_140sr_prism_off_writes_zero():
    m = ChauvetIntimidatorHybrid140SR_19Ch(1)
    m.set_prism(False)
    assert m.prism_on is False
    assert m.prism_rotate_speed == 0.0
    assert m.values[m.dmx_layout["prism1"]] == 0


def test_hybrid_140sr_prism_static_uses_static_plateau():
    m = ChauvetIntimidatorHybrid140SR_19Ch(1)
    m.set_prism(True, 0.0)
    assert m.prism_on is True
    assert m.prism_rotate_speed == 0.0
    # 8..12 is the static plateau per manual; we pick 10.
    v = m.values[m.dmx_layout["prism1"]]
    assert 8 <= v <= 12


def test_hybrid_140sr_prism_forward_rotation_in_range():
    m = ChauvetIntimidatorHybrid140SR_19Ch(1)
    m.set_prism(True, 1.0)
    assert m.values[m.dmx_layout["prism1"]] == 130
    m.set_prism(True, 0.5)
    v = m.values[m.dmx_layout["prism1"]]
    assert 13 <= v <= 130


def test_hybrid_140sr_prism_reverse_rotation_in_range():
    m = ChauvetIntimidatorHybrid140SR_19Ch(1)
    m.set_prism(True, -1.0)
    assert m.values[m.dmx_layout["prism1"]] == 247
    m.set_prism(True, -0.5)
    v = m.values[m.dmx_layout["prism1"]]
    assert 131 <= v <= 247


def test_hybrid_140sr_prism_rotate_speed_clamped():
    m = ChauvetIntimidatorHybrid140SR_19Ch(1)
    m.set_prism(True, 5.0)
    assert m.prism_rotate_speed == 1.0
    m.set_prism(True, -5.0)
    assert m.prism_rotate_speed == -1.0


def test_hybrid_140sr_13ch_prism_writes_prism1_channel():
    m = ChauvetIntimidatorHybrid140SR_13Ch(1)
    m.set_prism(True, 0.0)
    assert 8 <= m.values[m.dmx_layout["prism1"]] <= 12


def test_hybrid_140sr_rotating_gobo_slot_6_in_band():
    m = ChauvetIntimidatorHybrid140SR_19Ch(1)
    m.set_rotating_gobo(6, 0.0)
    # Rev.1 manual: Gobo 6 → 042–047 (midpoint 44).
    v = m.values[m.dmx_layout["rotating_gobo"]]
    assert 42 <= v <= 47
    # rotate_speed 0 → indexed/static (gobo_rotation = 0 "no function").
    assert m.values[m.dmx_layout["gobo_rotation"]] == 0
    assert m.get_rotating_gobo() == (6, 0.0)


def test_hybrid_140sr_rotating_gobo_forward_rotation_uses_forward_band():
    m = ChauvetIntimidatorHybrid140SR_19Ch(1)
    m.set_rotating_gobo(6, 1.0)
    # Rev.1: 006–116 rotation fast→slow (DMX 6 = fastest).
    assert m.values[m.dmx_layout["gobo_rotation"]] == 6
    m.set_rotating_gobo(6, 0.3)
    v = m.values[m.dmx_layout["gobo_rotation"]]
    assert 6 <= v <= 116


def test_hybrid_140sr_rotating_gobo_reverse_rotation_uses_reverse_band():
    m = ChauvetIntimidatorHybrid140SR_19Ch(1)
    m.set_rotating_gobo(6, -1.0)
    # Rev.1: 121–231 reverse (slow → fast); 231 = fastest.
    assert m.values[m.dmx_layout["gobo_rotation"]] == 231
    m.set_rotating_gobo(6, -0.5)
    v = m.values[m.dmx_layout["gobo_rotation"]]
    assert 121 <= v <= 231


def test_hybrid_140sr_13ch_rotating_gobo_writes_both_channels():
    m = ChauvetIntimidatorHybrid140SR_13Ch(1)
    m.set_rotating_gobo(6, 0.3)
    assert 42 <= m.values[m.dmx_layout["rotating_gobo"]] <= 47
    assert 6 <= m.values[m.dmx_layout["gobo_rotation"]] <= 116


def test_hybrid_140sr_rotating_gobo_slot_clamped():
    m = ChauvetIntimidatorHybrid140SR_19Ch(1)
    m.set_rotating_gobo(-3, 0.0)
    assert m.get_rotating_gobo()[0] == 0
    # Out-of-range high slot clamps to the top of the lookup table.
    m.set_rotating_gobo(99, 0.0)
    assert m.values[m.dmx_layout["rotating_gobo"]] == 58


def test_hybrid_140sr_focus_big_writes_zero():
    m = ChauvetIntimidatorHybrid140SR_19Ch(1)
    m.set_focus(0.0)
    assert m.get_focus() == 0.0
    assert m.values[m.dmx_layout["focus"]] == 0


def test_hybrid_140sr_focus_small_writes_full_scale():
    m = ChauvetIntimidatorHybrid140SR_19Ch(1)
    m.set_focus(1.0)
    assert m.values[m.dmx_layout["focus"]] == 255
    # Out-of-range values clamp to [0, 1].
    m.set_focus(5.0)
    assert m.get_focus() == 1.0
    m.set_focus(-0.5)
    assert m.get_focus() == 0.0
    assert m.values[m.dmx_layout["focus"]] == 0


def test_hybrid_140sr_13ch_focus_writes_focus_channel():
    m = ChauvetIntimidatorHybrid140SR_13Ch(1)
    m.set_focus(0.5)
    assert 120 <= m.values[m.dmx_layout["focus"]] <= 135
