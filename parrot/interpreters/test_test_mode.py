"""Tests for Mode.test interpreters."""

import math
import unittest
from unittest.mock import MagicMock

from parrot.director.color_scheme import ColorScheme
from parrot.director.frame import Frame, FrameSignal
from parrot.director.mode_dispatch import get_interpreter
from parrot.director.mode import Mode
from parrot.fixtures.led_par import Par
from parrot.fixtures.mirrorball import Mirrorball
from parrot.fixtures.moving_head import MovingHead
from parrot.interpreters.base import InterpreterArgs
from parrot.interpreters.move import MoveCircleSync
from parrot.interpreters.mode_test_interpreters import RigColorCycle
from parrot.utils.colour import Color


def _empty_frame(t: float) -> Frame:
    frame_values = {
        FrameSignal.freq_all: 0.0,
        FrameSignal.freq_high: 0.0,
        FrameSignal.freq_low: 0.0,
        FrameSignal.sustained_low: 0.0,
        FrameSignal.sustained_high: 0.0,
        FrameSignal.dampen: 0.0,
    }
    timeseries = {sig.name: [0.0] * 200 for sig in FrameSignal}
    f = Frame(frame_values, timeseries)
    f.time = t
    return f


class TestTestModeInterpreters(unittest.TestCase):
    def setUp(self):
        self.scheme = ColorScheme(
            Color("red"), Color("blue"), Color("white")
        )
        self.args = InterpreterArgs(50, True, 0, 100)

    def test_color_cycle_white_then_red_at_boundary(self):
        mh1 = MagicMock(spec=MovingHead)
        mh2 = MagicMock(spec=MovingHead)
        group = [mh1, mh2]
        tc = RigColorCycle(group, self.args)
        tc.step(_empty_frame(0.0), self.scheme)
        mh1.set_color.assert_called_with(Color("white"))
        mh2.set_color.assert_called_with(Color("white"))
        tc.step(_empty_frame(5.0), self.scheme)
        mh1.set_color.assert_called_with(Color("red"))
        mh2.set_color.assert_called_with(Color("red"))

    def test_move_circle_sync_identical_pan_tilt(self):
        m1 = MagicMock(spec=MovingHead)
        m2 = MagicMock(spec=MovingHead)
        ms = MoveCircleSync([m1, m2], self.args, multiplier=1.0, phase=0.0)
        f = _empty_frame(1.23)
        ms.step(f, self.scheme)
        t = 1.23
        expect_pan = math.cos(t) * 127 + 128
        expect_tilt = math.sin(t) * 127 + 128
        m1.set_pan.assert_called_once_with(expect_pan)
        m1.set_tilt.assert_called_once_with(expect_tilt)
        m2.set_pan.assert_called_once_with(expect_pan)
        m2.set_tilt.assert_called_once_with(expect_tilt)

    def test_get_interpreter_test_mode_par(self):
        p1 = MagicMock(spec=Par)
        p2 = MagicMock(spec=Par)
        interp = get_interpreter(Mode.test, [p1, p2], self.args)
        self.assertIn("RigColorCycle", str(interp))
        interp.step(_empty_frame(0.0), self.scheme)

    def test_get_interpreter_test_mode_mirrorball_full_dimmer(self):
        mb = MagicMock(spec=Mirrorball)
        interp = get_interpreter(Mode.test, [mb], self.args)
        interp.step(_empty_frame(0.0), self.scheme)
        mb.set_dimmer.assert_called_with(255)


if __name__ == "__main__":
    unittest.main()
