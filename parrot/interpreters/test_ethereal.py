"""Tests for the Mode.ethereal DSL entry in mode_interpretations."""

from unittest.mock import MagicMock, patch

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

    Ethereal drives sheer lights; chill / rave explicitly turn them
    off — all four use group matchers. Blackout and test don't reference groups.
    """
    assert mode_uses_group_matchers(Mode.ethereal) is True
    assert mode_uses_group_matchers(Mode.chill) is True
    assert mode_uses_group_matchers(Mode.rave) is True
    assert mode_uses_group_matchers(Mode.stroby) is True
    assert mode_uses_group_matchers(Mode.blackout) is False
    assert mode_uses_group_matchers(Mode.test) is False


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
        ChauvetRogueHybridRH1_19Ch,
    )

    args = InterpreterArgs(True)
    mh = ChauvetRogueHybridRH1_19Ch(1)
    mh.cloud_group_name = "sheer lights"
    interp = get_interpreter(Mode.ethereal, [mh], args)
    scheme = ColorScheme(Color("red"), Color("blue"), Color("white"))
    interp.step(_frame(), scheme)
    on, speed = mh.get_prism()
    assert on is True
    assert speed > 0.0
    # Prism 1 DMX channel should be in the forward-rotation band (13..130).
    v = mh.values[mh.dmx_layout["prism1"]]
    assert 13 <= v <= 130


def test_ethereal_dsl_applies_rotating_gobo_6_to_hybrid_beams() -> None:
    from parrot.fixtures.chauvet.rogue_hybrid_rh1 import (
        ChauvetRogueHybridRH1_19Ch,
    )

    args = InterpreterArgs(True)
    mh = ChauvetRogueHybridRH1_19Ch(1)
    mh.cloud_group_name = "sheer lights"
    interp = get_interpreter(Mode.ethereal, [mh], args)
    scheme = ColorScheme(Color("red"), Color("blue"), Color("white"))
    interp.step(_frame(), scheme)
    slot, speed = mh.get_rotating_gobo()
    assert slot == 6
    assert speed > 0.0
    # Rotating gobo 6 band is DMX 042..047 per the QRG.
    v = mh.values[mh.dmx_layout["rotating_gobo"]]
    assert 42 <= v <= 47
    # Rotation channel must be inside the forward-rotation band (64..144).
    gr = mh.values[mh.dmx_layout["gobo_rotation"]]
    assert 64 <= gr <= 144


def test_ethereal_dsl_applies_focus_big_to_hybrid_beams() -> None:
    from parrot.fixtures.chauvet.rogue_hybrid_rh1 import (
        ChauvetRogueHybridRH1_19Ch,
    )

    args = InterpreterArgs(True)
    mh = ChauvetRogueHybridRH1_19Ch(1)
    mh.cloud_group_name = "sheer lights"
    interp = get_interpreter(Mode.ethereal, [mh], args)
    scheme = ColorScheme(Color("red"), Color("blue"), Color("white"))
    interp.step(_frame(), scheme)
    assert mh.get_focus() == 0.0
    assert mh.values[mh.dmx_layout["focus"]] == 0


def test_ethereal_dsl_uses_slow_breath_within_configured_range() -> None:
    """SlowBreath replaces GentlePulse on sheer lights: dimmer stays inside [0.25, 0.85]*255
    regardless of frame.time, with no audio signal required."""
    from parrot.fixtures.chauvet.rogue_hybrid_rh1 import (
        ChauvetRogueHybridRH1_19Ch,
    )

    args = InterpreterArgs(True)
    mh = ChauvetRogueHybridRH1_19Ch(1)
    mh.cloud_group_name = "sheer lights"
    interp = get_interpreter(Mode.ethereal, [mh], args)
    scheme = ColorScheme(Color("red"), Color("blue"), Color("white"))
    frame = _frame()
    seen: list[float] = []
    for t in (0.0, 2.5, 5.0, 7.5, 10.0, 14.0):
        frame.time = t
        interp.step(frame, scheme)
        seen.append(mh.get_dimmer())
    for dim in seen:
        assert 0.25 * 255 - 1.0 <= dim <= 0.85 * 255 + 1.0
    # Dimmer must actually move (not stuck) across a full breathing period.
    assert max(seen) - min(seen) > 5.0


def test_ethereal_sheer_slow_breath_moves_dimmer() -> None:
    """Ethereal sheer group still picks SlowBreath breathing (not collapsed to Dimmer0)."""
    from parrot.fixtures.chauvet.rogue_hybrid_rh1 import (
        ChauvetRogueHybridRH1_19Ch,
    )

    args = InterpreterArgs(True)
    mh = ChauvetRogueHybridRH1_19Ch(1)
    mh.cloud_group_name = "sheer lights"
    interp = get_interpreter(Mode.ethereal, [mh], args)
    scheme = ColorScheme(Color("red"), Color("blue"), Color("white"))
    frame = _frame()
    dims: list[float] = []
    for t in (0.0, 3.5, 7.0, 10.5, 14.0):
        frame.time = t
        interp.step(frame, scheme)
        dims.append(mh.get_dimmer())
    assert max(dims) - min(dims) > 5.0
    for dim in dims:
        assert 0.25 * 255 - 1.0 <= dim <= 0.85 * 255 + 1.0
