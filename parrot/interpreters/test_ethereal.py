"""Tests for the Mode.ethereal DSL entry in mode_interpretations."""

from unittest.mock import MagicMock, patch

from parrot.director.color_scheme import ColorScheme
from parrot.director.frame import Frame, FrameSignal
from parrot.director.mode import Mode
from parrot.director.mode_interpretations import (
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


def test_mode_uses_group_matchers_flags_ethereal_only() -> None:
    assert mode_uses_group_matchers(Mode.ethereal) is True
    assert mode_uses_group_matchers(Mode.chill) is False
    assert mode_uses_group_matchers(Mode.rave) is False


def test_ethereal_dsl_fades_mirrorball_and_zeros_unlisted() -> None:
    args = InterpreterArgs(50, True, 0, 100)
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
    args = InterpreterArgs(50, True, 0, 100)
    mh = ChauvetSpot160_12Ch(1)
    mh.cloud_group_name = "sheer lights"
    par = MagicMock(spec=MovingHead)
    par.cloud_group_name = "other"
    interp = get_interpreter(Mode.ethereal, [mh, par], args)
    scheme = ColorScheme(Color("red"), Color("blue"), Color("white"))
    interp.step(_frame(), scheme)
    par.set_dimmer.assert_called_with(0)
    assert mh.get_pan_angle() != 0.0 or mh.get_tilt_angle() != 0.0
