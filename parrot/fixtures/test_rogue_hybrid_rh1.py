"""Tests for Chauvet Rogue™ RH1 Hybrid DMX mapping (``rogue_hybrid_rh1`` module).

Channel layout and DMX-value bands are taken from the *Rogue™ RH1 Hybrid User
Manual Rev. 4* (Chauvet Professional, Sept 2015). The 20CH personality is the
default; the 25CH personality adds Fine Dimmer / Fine Focus / Fine Zoom and
Movement-Macro channels but keeps the same role for every overlapping slot.
"""

from parrot.fixtures.chauvet.rogue_hybrid_rh1 import (
    ChauvetRogueHybridRH1_20Ch,
    ChauvetRogueHybridRH1_25Ch,
)


def test_rh1_advertises_prism_and_focus():
    """RH1 Hybrid has both a 6-facet prism and a variable-focus optic; the
    rendering capability flags must stay True so desktop/web previews show
    the splay fan and narrowing beam when interpreters engage them."""
    m20 = ChauvetRogueHybridRH1_20Ch(1)
    m25 = ChauvetRogueHybridRH1_25Ch(1)
    assert m20.supports_prism is True
    assert m20.supports_focus is True
    assert m25.supports_prism is True
    assert m25.supports_focus is True


def test_rh1_20ch_width_and_dimmer_channel():
    m = ChauvetRogueHybridRH1_20Ch(1)
    assert m.width == 20
    assert len(m.values) == 20
    # 20CH ch 6 (index 5) is Dimmer per Rev. 4 manual.
    m.set_dimmer(255)
    assert m.values[5] == 255


def test_rh1_25ch_width_and_dimmer_channel():
    m = ChauvetRogueHybridRH1_25Ch(1)
    assert m.width == 25
    assert len(m.values) == 25
    # 25CH ch 6 (index 5) is still Dimmer; ch 7 (index 6) is Fine Dimmer.
    m.set_dimmer(255)
    assert m.values[5] == 255
    assert "dimmer_fine" in m.dmx_layout


def test_rh1_caps_interpreter_strobe_to_slower_shutter_band():
    """Full-scale strobe should stay in a slower RH1-specific band, not at 131."""
    m20 = ChauvetRogueHybridRH1_20Ch(1)
    m25 = ChauvetRogueHybridRH1_25Ch(1)

    for m in (m20, m25):
        m.set_strobe(255)
        assert m.strobe_shutter_lower == 16
        assert m.strobe_shutter_upper == 64
        assert m.values[m.dmx_layout["shutter"]] == 64


def test_rh1_prism_off_writes_zero_to_both_prism_channels():
    """Per Rev. 4, prism insert and prism rotation live on separate channels."""
    m = ChauvetRogueHybridRH1_20Ch(1)
    m.set_prism(False)
    assert m.prism_on is False
    assert m.prism_rotate_speed == 0.0
    assert m.values[m.dmx_layout["prism1"]] == 0
    assert m.values[m.dmx_layout["prism1_rotate"]] == 0


def test_rh1_prism_static_inserts_prism_with_no_rotation():
    """Static prism: insert engaged (CH 14 in the 005–255 band) but rotate channel idle."""
    m = ChauvetRogueHybridRH1_20Ch(1)
    m.set_prism(True, 0.0)
    assert m.prism_on is True
    assert m.prism_rotate_speed == 0.0
    insert = m.values[m.dmx_layout["prism1"]]
    assert 5 <= insert <= 255
    # Rotate channel sits in the indexed/static band (000–127).
    assert m.values[m.dmx_layout["prism1_rotate"]] == 0


def test_rh1_prism_forward_rotation_uses_cw_band_on_rotate_channel():
    """CH 15 CW band per Rev. 4: 128 (fast) → 189 (slow)."""
    m = ChauvetRogueHybridRH1_20Ch(1)
    m.set_prism(True, 1.0)
    assert m.values[m.dmx_layout["prism1_rotate"]] == 128
    m.set_prism(True, 0.5)
    rot = m.values[m.dmx_layout["prism1_rotate"]]
    assert 128 <= rot <= 189


def test_rh1_prism_reverse_rotation_uses_ccw_band_on_rotate_channel():
    """CH 15 CCW band per Rev. 4: 194 (slow) → 255 (fast)."""
    m = ChauvetRogueHybridRH1_20Ch(1)
    m.set_prism(True, -1.0)
    assert m.values[m.dmx_layout["prism1_rotate"]] == 255
    m.set_prism(True, -0.5)
    rot = m.values[m.dmx_layout["prism1_rotate"]]
    assert 194 <= rot <= 255


def test_rh1_prism_rotate_speed_clamped():
    m = ChauvetRogueHybridRH1_20Ch(1)
    m.set_prism(True, 5.0)
    assert m.prism_rotate_speed == 1.0
    m.set_prism(True, -5.0)
    assert m.prism_rotate_speed == -1.0


def test_rh1_25ch_prism_writes_split_channels():
    m = ChauvetRogueHybridRH1_25Ch(1)
    m.set_prism(True, 0.0)
    assert 5 <= m.values[m.dmx_layout["prism1"]] <= 255
    assert m.values[m.dmx_layout["prism1_rotate"]] == 0


def test_rh1_rotating_gobo_slot_6_in_band():
    """Per Rev. 4 manual gobo wheel 2: Gobo 6 → 036–041 (midpoint 38)."""
    m = ChauvetRogueHybridRH1_20Ch(1)
    m.set_rotating_gobo(6, 0.0)
    v = m.values[m.dmx_layout["rotating_gobo"]]
    assert 36 <= v <= 41
    # rotate_speed 0 → static (gobo_rotation = 0 = "Gobo index" band)
    assert m.values[m.dmx_layout["gobo_rotation"]] == 0
    assert m.get_rotating_gobo() == (6, 0.0)


def test_rh1_rotating_gobo_slot_0_is_open():
    """Slot 0 → open band on CH 10 (DMX 0)."""
    m = ChauvetRogueHybridRH1_20Ch(1)
    m.set_rotating_gobo(0, 0.0)
    assert m.values[m.dmx_layout["rotating_gobo"]] == 0


def test_rh1_rotating_gobo_forward_rotation_uses_cw_band():
    """CH 11 CW band per Rev. 4: 064 (slow) → 147 (fast)."""
    m = ChauvetRogueHybridRH1_20Ch(1)
    m.set_rotating_gobo(6, 1.0)
    assert m.values[m.dmx_layout["gobo_rotation"]] == 147
    m.set_rotating_gobo(6, 0.3)
    gr = m.values[m.dmx_layout["gobo_rotation"]]
    assert 64 <= gr <= 147


def test_rh1_rotating_gobo_reverse_rotation_uses_ccw_band():
    """CH 11 CCW band per Rev. 4: 148 (fast) → 231 (slow)."""
    m = ChauvetRogueHybridRH1_20Ch(1)
    m.set_rotating_gobo(6, -1.0)
    assert m.values[m.dmx_layout["gobo_rotation"]] == 148
    m.set_rotating_gobo(6, -0.5)
    gr = m.values[m.dmx_layout["gobo_rotation"]]
    assert 148 <= gr <= 231


def test_rh1_25ch_rotating_gobo_writes_both_channels():
    m = ChauvetRogueHybridRH1_25Ch(1)
    m.set_rotating_gobo(6, 0.3)
    assert 36 <= m.values[m.dmx_layout["rotating_gobo"]] <= 41
    assert 64 <= m.values[m.dmx_layout["gobo_rotation"]] <= 147


def test_rh1_rotating_gobo_slot_clamped():
    """Out-of-range slot indices clamp to the lookup table bounds."""
    m = ChauvetRogueHybridRH1_20Ch(1)
    m.set_rotating_gobo(-3, 0.0)
    # MovingHead.set_rotating_gobo() floors negative slots to 0 (open).
    assert m.get_rotating_gobo()[0] == 0
    assert m.values[m.dmx_layout["rotating_gobo"]] == 0
    # Out-of-range high slot clamps to the top of the lookup table (Gobo 9 → 58).
    m.set_rotating_gobo(99, 0.0)
    assert m.values[m.dmx_layout["rotating_gobo"]] == 58


def test_rh1_focus_big_writes_zero():
    m = ChauvetRogueHybridRH1_20Ch(1)
    m.set_focus(0.0)
    assert m.get_focus() == 0.0
    assert m.values[m.dmx_layout["focus"]] == 0


def test_rh1_focus_small_writes_full_scale():
    m = ChauvetRogueHybridRH1_20Ch(1)
    m.set_focus(1.0)
    assert m.values[m.dmx_layout["focus"]] == 255
    # Out-of-range values clamp to [0, 1].
    m.set_focus(5.0)
    assert m.get_focus() == 1.0
    m.set_focus(-0.5)
    assert m.get_focus() == 0.0
    assert m.values[m.dmx_layout["focus"]] == 0


def test_rh1_25ch_focus_writes_focus_channel():
    m = ChauvetRogueHybridRH1_25Ch(1)
    m.set_focus(0.5)
    assert 120 <= m.values[m.dmx_layout["focus"]] <= 135


def test_rh1_startup_sequence_holds_blackout_macros_on_control_channel():
    """During startup the 20CH driver should strike the lamp, then latch CH 20
    (Control) into the color-wheel and gobo-wheel "blackout while moving" bands
    (manual page 30), then release the channel back to 0."""
    import time as _time
    from unittest.mock import MagicMock, patch

    m = ChauvetRogueHybridRH1_20Ch(1)
    ctrl = m.dmx_layout["control"]
    dmx = MagicMock()

    base = _time.time()
    with patch("parrot.fixtures.chauvet.mover_base.time.time") as t:
        # First render: enters phase 0 — lamp on (130–139).
        t.return_value = base
        m.render(dmx)
        assert 130 <= m.values[ctrl] <= 139

        # After the 1 s lamp-on hold, step into color-wheel blackout (090–099).
        t.return_value = base + 1.1
        m.render(dmx)
        assert 90 <= m.values[ctrl] <= 99

        # Advance virtual time past the color-wheel hold to step into gobo blackout.
        t.return_value = base + 4.2
        m.render(dmx)
        assert 110 <= m.values[ctrl] <= 119  # gobo-wheel blackout band

        # After both holds expire, control is parked at 0 (no function).
        t.return_value = base + 7.3
        m.render(dmx)
        assert m.values[ctrl] == 0


def test_rh1_startup_sequence_reasserts_control_hold_to_dmx():
    import time as _time
    from unittest.mock import MagicMock, patch

    m = ChauvetRogueHybridRH1_20Ch(1)
    ctrl = m.dmx_layout["control"]
    control_channel = m.address + ctrl
    dmx = MagicMock()
    base = _time.time()

    with patch("parrot.fixtures.chauvet.mover_base.time.time") as t:
        t.return_value = base
        m.render(dmx)

        t.return_value = base + 1.1
        m.render(dmx)
        dmx.set_channel.assert_any_call(
            control_channel,
            95,
            universe=m.universe,
        )

        dmx.reset_mock()
        m.values[ctrl] = 0
        t.return_value = base + 2.0
        m.render(dmx)

        assert m.values[ctrl] == 95
        dmx.set_channel.assert_any_call(
            control_channel,
            95,
            universe=m.universe,
        )
