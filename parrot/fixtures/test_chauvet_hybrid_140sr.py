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
    # QRG Rev5 rotating gobo 6 band is DMX 042..047.
    v = m.values[m.dmx_layout["rotating_gobo"]]
    assert 42 <= v <= 47
    # rotate_speed 0 → indexed/static (gobo_rotation = 0 "no function").
    assert m.values[m.dmx_layout["gobo_rotation"]] == 0
    assert m.get_rotating_gobo() == (6, 0.0)


def test_hybrid_140sr_rotating_gobo_forward_rotation_uses_forward_band():
    m = ChauvetIntimidatorHybrid140SR_19Ch(1)
    m.set_rotating_gobo(6, 1.0)
    # Forward rotation band is 64..144 (fast → slow).
    assert m.values[m.dmx_layout["gobo_rotation"]] == 64
    m.set_rotating_gobo(6, 0.3)
    v = m.values[m.dmx_layout["gobo_rotation"]]
    assert 64 <= v <= 144


def test_hybrid_140sr_rotating_gobo_reverse_rotation_uses_reverse_band():
    m = ChauvetIntimidatorHybrid140SR_19Ch(1)
    m.set_rotating_gobo(6, -1.0)
    # Reverse rotation band is 152..231 (slow → fast).
    assert m.values[m.dmx_layout["gobo_rotation"]] == 231
    m.set_rotating_gobo(6, -0.5)
    v = m.values[m.dmx_layout["gobo_rotation"]]
    assert 152 <= v <= 231


def test_hybrid_140sr_13ch_rotating_gobo_writes_both_channels():
    m = ChauvetIntimidatorHybrid140SR_13Ch(1)
    m.set_rotating_gobo(6, 0.3)
    assert 42 <= m.values[m.dmx_layout["rotating_gobo"]] <= 47
    assert 64 <= m.values[m.dmx_layout["gobo_rotation"]] <= 144


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
