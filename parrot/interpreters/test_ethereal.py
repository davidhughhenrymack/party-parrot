"""Tests for the Mode.ethereal DSL entry in mode_interpretations."""

from unittest.mock import MagicMock, patch

import pytest

from parrot.director.color_scheme import ColorScheme
from parrot.director.frame import Frame, FrameSignal
from parrot.director.mode import Mode
from parrot.director.mode_dispatch import (
    Group,
    get_interpreter,
    mode_uses_group_matchers,
)
from parrot.fixtures.chauvet.intimidator160 import ChauvetSpot160_12Ch
from parrot.fixtures.led_par import Par
from parrot.fixtures.mirrorball import Mirrorball
from parrot.fixtures.moving_head import MovingHead
from parrot.interpreters.base import InterpreterArgs
from parrot.utils.colour import Color


def _frame() -> Frame:
    fv = {s: 0.0 for s in FrameSignal}
    ts = {s.name: [0.0] * 50 for s in FrameSignal}
    f = Frame(fv, ts)
    f.time = 100.0
    return f


def test_group_matcher_is_case_insensitive() -> None:
    mh = MagicMock(spec=MovingHead)
    mh.cloud_group_name = "  Sheer Lights  "
    assert Group("sheer lights").matches(mh) is True
    mh.cloud_group_name = "other"
    assert Group("sheer lights").matches(mh) is False


def test_mode_uses_group_matchers_for_modes_that_silence_sheer_lights() -> None:
    """Any mode with a ``Group(...)`` key in its DSL flips into group-aware dispatch.

    Ethereal drives sheer lights; chill / rave explicitly turn them off. Test
    and home use the track group for mirrorball named-position support.
    """
    assert mode_uses_group_matchers(Mode.ethereal) is True
    assert mode_uses_group_matchers(Mode.chill) is True
    assert mode_uses_group_matchers(Mode.rave) is True
    assert mode_uses_group_matchers(Mode.stroby) is True
    assert mode_uses_group_matchers(Mode.blackout) is False
    assert mode_uses_group_matchers(Mode.test) is True
    assert mode_uses_group_matchers(Mode.home) is True


def test_ethereal_dsl_fades_mirrorball_and_zeros_unlisted() -> None:
    args = InterpreterArgs(True)
    mb = Mirrorball(1)
    par = MagicMock(spec=Par)
    par.cloud_group_name = None
    scheme = ColorScheme(Color("red"), Color("blue"), Color("white"))
    with patch(
        "parrot.interpreters.dimmer.time.perf_counter",
        side_effect=[0.0] + [100.0] * 8,
    ):
        interp = get_interpreter(Mode.ethereal, [mb, par], args)
        interp.step(_frame(), scheme)
    par.set_dimmer.assert_called_with(0)
    assert mb.get_dimmer() == 255.0


def test_ethereal_dsl_drives_sheer_moving_heads_and_zeros_others() -> None:
    args = InterpreterArgs(True)
    mh = ChauvetSpot160_12Ch(1)
    mh.cloud_group_name = "sheer lights"
    par = MagicMock(spec=MovingHead)
    par.cloud_group_name = "other"
    interp = get_interpreter(Mode.ethereal, [mh, par], args)
    scheme = ColorScheme(Color("red"), Color("blue"), Color("white"))
    interp.step(_frame(), scheme)
    par.set_dimmer.assert_called_with(0)
    assert mh.get_pan_angle() != 0.0 or mh.get_tilt_angle() != 0.0


def test_ethereal_dsl_turns_prism_on_for_sheer_moving_heads() -> None:
    from parrot.fixtures.chauvet.rogue_hybrid_rh1 import (
        ChauvetRogueHybridRH1_20Ch,
    )

    args = InterpreterArgs(True)
    mh = ChauvetRogueHybridRH1_20Ch(1)
    mh.cloud_group_name = "sheer lights"
    interp = get_interpreter(Mode.ethereal, [mh], args)
    scheme = ColorScheme(Color("red"), Color("blue"), Color("white"))
    interp.step(_frame(), scheme)
    on, speed = mh.get_prism()
    assert on is True
    assert speed > 0.0
    # CH 14 Prism 1: insert engaged (anywhere in 005–255).
    insert = mh.values[mh.dmx_layout["prism1"]]
    assert 5 <= insert <= 255
    # CH 15 Prism 1 Rotate forward-rotation band per Rev. 4 manual: 128..189.
    rot = mh.values[mh.dmx_layout["prism1_rotate"]]
    assert 128 <= rot <= 189


def test_ethereal_dsl_applies_rotating_gobo_6_to_hybrid_beams() -> None:
    from parrot.fixtures.chauvet.rogue_hybrid_rh1 import (
        ChauvetRogueHybridRH1_20Ch,
    )

    args = InterpreterArgs(True)
    mh = ChauvetRogueHybridRH1_20Ch(1)
    mh.cloud_group_name = "sheer lights"
    interp = get_interpreter(Mode.ethereal, [mh], args)
    scheme = ColorScheme(Color("red"), Color("blue"), Color("white"))
    interp.step(_frame(), scheme)
    slot, speed = mh.get_rotating_gobo()
    assert slot == 6
    assert speed > 0.0
    # Rev. 4 manual gobo wheel 2: Gobo 6 → DMX 036–041 (midpoint 38).
    v = mh.values[mh.dmx_layout["rotating_gobo"]]
    assert 36 <= v <= 41
    # CH 11 Gobo Wheel 2 Rotate forward band per Rev. 4: 064..147.
    gr = mh.values[mh.dmx_layout["gobo_rotation"]]
    assert 64 <= gr <= 147


def test_ethereal_dsl_applies_phased_sine_focus_to_hybrid_beams() -> None:
    from parrot.fixtures.chauvet.rogue_hybrid_rh1 import (
        ChauvetRogueHybridRH1_20Ch,
    )

    args = InterpreterArgs(True)
    movers = [ChauvetRogueHybridRH1_20Ch(1 + i * 20) for i in range(4)]
    for mh in movers:
        mh.cloud_group_name = "sheer lights"
    interp = get_interpreter(Mode.ethereal, movers, args)
    scheme = ColorScheme(Color("red"), Color("blue"), Color("white"))
    frame = _frame()
    frame.time = 0.0

    interp.step(frame, scheme)

    # Four fixtures spread over sine phases 0, π/2, π, 3π/2 at t=0:
    # focus = 0.5 + 0.5*sin(phase) → 0.5, 1.0, 0.5, 0.0.
    focuses = [mh.get_focus() for mh in movers]
    assert focuses[0] == pytest.approx(0.5, abs=0.02)
    assert focuses[1] == pytest.approx(1.0, abs=0.02)
    assert focuses[2] == pytest.approx(0.5, abs=0.02)
    assert focuses[3] == pytest.approx(0.0, abs=0.02)
    for mh in movers:
        assert mh.values[mh.dmx_layout["focus"]] == pytest.approx(
            round(mh.get_focus() * 255), abs=1.0
        )


def test_ethereal_dsl_uses_low_freq_decay_with_70_percent_floor() -> None:
    """Sheer moving heads sit at 70%, jump brighter on kick energy, then decay."""
    from parrot.fixtures.chauvet.rogue_hybrid_rh1 import (
        ChauvetRogueHybridRH1_20Ch,
    )

    args = InterpreterArgs(True)
    mh = ChauvetRogueHybridRH1_20Ch(1)
    mh.cloud_group_name = "sheer lights"
    interp = get_interpreter(Mode.ethereal, [mh], args)
    scheme = ColorScheme(Color("red"), Color("blue"), Color("white"))
    frame = _frame()

    # No low-frequency signal: hold the 70% floor.
    frame.values[FrameSignal.freq_low] = 0.0
    interp.step(frame, scheme)
    floor = mh.get_dimmer()
    assert floor == pytest.approx(0.7 * 255, abs=1.0)

    # Kick hit: lift immediately to the 100% ceiling.
    frame.values[FrameSignal.freq_low] = 1.0
    interp.step(frame, scheme)
    peak = mh.get_dimmer()
    assert peak == pytest.approx(255, abs=1.0)

    # Signal drops: decay toward the 70% floor instead of snapping down.
    frame.values[FrameSignal.freq_low] = 0.0
    interp.step(frame, scheme)
    after_one_decay = mh.get_dimmer()
    assert floor < after_one_decay < peak
    assert after_one_decay == pytest.approx(0.9 * 255, abs=1.0)

    for _ in range(12):
        interp.step(frame, scheme)
    assert 0.7 * 255 - 1.0 <= mh.get_dimmer() < after_one_decay


def test_ethereal_sheer_low_freq_decay_applies_to_whole_group() -> None:
    """The low-frequency decay dimmer drives all sheer movers together."""
    from parrot.fixtures.chauvet.rogue_hybrid_rh1 import (
        ChauvetRogueHybridRH1_20Ch,
    )

    args = InterpreterArgs(True)
    movers = [ChauvetRogueHybridRH1_20Ch(1 + i * 20) for i in range(3)]
    for mh in movers:
        mh.cloud_group_name = "sheer lights"
    interp = get_interpreter(Mode.ethereal, movers, args)
    scheme = ColorScheme(Color("red"), Color("blue"), Color("white"))
    frame = _frame()
    frame.values[FrameSignal.freq_low] = 0.5

    interp.step(frame, scheme)

    expected = (0.7 + 0.3 * 0.5) * 255
    dims = [mh.get_dimmer() for mh in movers]
    assert dims == pytest.approx([expected, expected, expected], abs=1.0)
