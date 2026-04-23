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
from parrot.interpreters.mode_test_interpreters import (
    PanTiltAxisCheck,
    RigColorCycle,
)
from parrot.utils.colour import Color


def _empty_frame(t: float) -> Frame:
    frame_values = {
        FrameSignal.freq_all: 0.0,
        FrameSignal.freq_high: 0.0,
        FrameSignal.freq_low: 0.0,
        FrameSignal.sustained_low: 0.0,
        FrameSignal.sustained_high: 0.0,
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
        self.args = InterpreterArgs(True)

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

    def test_pan_tilt_axis_check_hold_travel_phases(self):
        """Each excursion holds at home, lerps to the extreme, holds, and lerps back.

        Samples the four phases for the first excursion (tilt up) plus the
        hold-at-extreme for each of the four extremes to prove the sequence
        visits all of them.
        """
        hold = PanTiltAxisCheck.HOLD_SECONDS
        travel = PanTiltAxisCheck.TRAVEL_SECONDS
        cycle = 2 * hold + 2 * travel

        # Phase checks for the first excursion (home → tilt-up → home).
        self.assertEqual(PanTiltAxisCheck.position_at(hold / 2), (127.0, 127.0))
        # midway through the out-travel: halfway between (127,127) and (127,255)
        self.assertEqual(
            PanTiltAxisCheck.position_at(hold + travel / 2),
            (127.0, 127.0 + (255 - 127) * 0.5),
        )
        # hold at the extreme:
        self.assertEqual(
            PanTiltAxisCheck.position_at(hold + travel + hold / 2), (127.0, 255.0)
        )
        # midway through the return-travel: halfway between (127,255) and (127,127)
        self.assertEqual(
            PanTiltAxisCheck.position_at(hold + travel + hold + travel / 2),
            (127.0, 255.0 + (127 - 255) * 0.5),
        )

        # Hold-at-extreme sample for each of the four excursions (tilt up,
        # tilt down, pan left, pan right) — one tick into the extreme hold.
        for i, extreme in enumerate(PanTiltAxisCheck.EXTREMES):
            t = i * cycle + hold + travel + hold / 2
            self.assertEqual(
                PanTiltAxisCheck.position_at(t),
                (float(extreme[0]), float(extreme[1])),
            )

    def test_pan_tilt_axis_check_step_interpolates_on_fixtures(self):
        """step() should push the interpolated pan/tilt to every fixture in the group."""
        mh = MagicMock(spec=MovingHead)
        checker = PanTiltAxisCheck([mh], self.args)
        hold = PanTiltAxisCheck.HOLD_SECONDS
        travel = PanTiltAxisCheck.TRAVEL_SECONDS
        # Mid-travel-out on the first extreme (tilt up): tilt should be 50% between 127 and 255.
        checker.step(_empty_frame(hold + travel * 0.5), self.scheme)
        mh.set_pan.assert_called_once_with(127.0)
        mh.set_tilt.assert_called_once_with(127.0 + (255 - 127) * 0.5)

    def test_pan_tilt_axis_check_wraps_modulo(self):
        """After one full cycle, time t = cycle is back at home start-of-hold."""
        mh = MagicMock(spec=MovingHead)
        checker = PanTiltAxisCheck([mh], self.args)
        full_cycle = (
            2 * PanTiltAxisCheck.HOLD_SECONDS + 2 * PanTiltAxisCheck.TRAVEL_SECONDS
        ) * len(PanTiltAxisCheck.EXTREMES)
        checker.step(_empty_frame(full_cycle + 0.1), self.scheme)
        mh.set_pan.assert_called_once_with(127.0)
        mh.set_tilt.assert_called_once_with(127.0)

    def test_get_interpreter_test_mode_moving_head_uses_axis_check(self):
        from parrot.fixtures.chauvet.intimidator160 import ChauvetSpot160_12Ch

        mh = ChauvetSpot160_12Ch(1)
        interp = get_interpreter(Mode.test, [mh], self.args)
        self.assertIn("PanTiltAxisCheck", str(interp))

    def test_get_interpreter_test_mode_mirrorball_full_dimmer(self):
        mb = MagicMock(spec=Mirrorball)
        interp = get_interpreter(Mode.test, [mb], self.args)
        interp.step(_empty_frame(0.0), self.scheme)
        mb.set_dimmer.assert_called_with(255)


if __name__ == "__main__":
    unittest.main()
