import unittest
from unittest.mock import MagicMock
from parrot.director.frame import Frame, FrameSignal
from parrot.director.mode_dispatch import get_interpreter
from parrot.director.mode import Mode
from parrot.interpreters.base import InterpreterArgs
from parrot.fixtures.led_par import Par
from parrot.fixtures.mirrorball import Mirrorball
from parrot.fixtures.motionstrip import Motionstrip
from parrot.interpreters.dimmer import Dimmer0
from parrot.director.color_scheme import ColorScheme
from parrot.utils.colour import Color
import random


class TestModes(unittest.TestCase):
    def setUp(self):
        # Create a test frame with some activity
        frame_values = {
            FrameSignal.freq_all: 0.8,  # High value to trigger beat detection
            FrameSignal.freq_high: 0.8,  # High value to trigger beat detection
            FrameSignal.freq_low: 0.8,  # High value to trigger beat detection
            FrameSignal.sustained_low: 0.1,
            FrameSignal.sustained_high: 0.8,  # High value to trigger effects
            FrameSignal.dampen: 0.0,  # Keep dampen signal low to allow light activation
        }
        timeseries = {
            FrameSignal.freq_all.name: [0.8] * 200,
            FrameSignal.freq_high.name: [0.8] * 200,
            FrameSignal.freq_low.name: [0.8] * 200,
            FrameSignal.sustained_low.name: [0.1] * 200,
            FrameSignal.sustained_high.name: [0.8] * 200,
            FrameSignal.dampen.name: [0.0]
            * 200,  # Keep dampen signal low in timeseries
        }
        self.frame = Frame(frame_values, timeseries)
        self.args = InterpreterArgs(50, True, 0, 100)

        # Create a test color scheme
        self.scheme = ColorScheme(
            Color("red"), Color("blue"), Color("white")  # fg  # bg  # bg_contrast
        )

        # Create some mock fixtures
        self.par1 = MagicMock(spec=Par)
        self.par2 = MagicMock(spec=Par)
        self.par3 = MagicMock(spec=Par)
        self.pars = [self.par1, self.par2, self.par3]

        self.strip1 = MagicMock(spec=Motionstrip)
        self.strip2 = MagicMock(spec=Motionstrip)
        self.strips = [self.strip1, self.strip2]

        # Set up mock bulbs for Motionstrip fixtures
        for strip in self.strips:
            mock_bulbs = [
                MagicMock(spec=Par),
                MagicMock(spec=Par),
                MagicMock(spec=Par),
            ]  # 3 bulbs per strip
            strip.get_bulbs.return_value = mock_bulbs
            for bulb in mock_bulbs:
                bulb.get_dimmer.return_value = 0.0

        # Set initial dimmer values to 0
        for fixture in self.pars + self.strips:
            fixture.get_dimmer.return_value = 0.0

        # Ensure consistent random behavior
        random.seed(42)

    def test_chill_mode_interpreter(self):
        """Test that chill mode returns valid interpreters"""
        # Test with Par fixtures
        interpreter = get_interpreter(Mode.chill, self.pars, self.args)
        self.assertIsNotNone(interpreter)

        # Should not crash when stepping
        interpreter.step(self.frame, self.scheme)

        # Test with Motionstrip fixtures
        interpreter = get_interpreter(Mode.chill, self.strips, self.args)
        self.assertIsNotNone(interpreter)

        # Should not crash when stepping
        interpreter.step(self.frame, self.scheme)

    def test_all_modes_have_interpreters(self):
        """Test that all modes return valid interpreters for common fixtures"""
        for mode in [
            Mode.rave,
            Mode.chill,
            Mode.rave_gentle,
            Mode.blackout,
            Mode.test,
            Mode.ethereal,
        ]:
            # Test with Par fixtures
            interpreter = get_interpreter(mode, self.pars, self.args)
            self.assertIsNotNone(interpreter)

            # Should not crash when stepping
            interpreter.step(self.frame, self.scheme)

    def test_sheer_lights_are_silenced_in_chill_and_rave_gentle(self):
        """Sheer lights are an Ethereal/Rave feature only — chill and rave_gentle keep them off."""
        from parrot.fixtures.chauvet.intimidator_hybrid_140sr import (
            ChauvetIntimidatorHybrid140SR_19Ch,
        )

        for mode in (Mode.chill, Mode.rave_gentle):
            sheer = ChauvetIntimidatorHybrid140SR_19Ch(1)
            sheer.cloud_group_name = "sheer lights"
            other = ChauvetIntimidatorHybrid140SR_19Ch(20)
            other.cloud_group_name = None

            interp = get_interpreter(mode, [sheer, other], self.args)
            interp.step(self.frame, self.scheme)

            assert sheer.get_dimmer() == 0, (
                f"{mode}: sheer-grouped moving head should be Dimmer0, got {sheer.get_dimmer()}"
            )

    def test_rave_sheer_lights_randomize_prism_and_focus(self):
        """Rave gives each sheer-grouped mover its own prism/focus — the group mustn't be uniform."""
        import random as _random
        from parrot.fixtures.chauvet.intimidator_hybrid_140sr import (
            ChauvetIntimidatorHybrid140SR_19Ch,
        )

        # Seed so the test is deterministic but still exercises randomization.
        _random.seed(12345)
        movers = [
            ChauvetIntimidatorHybrid140SR_19Ch(1 + i * 20) for i in range(8)
        ]
        for m in movers:
            m.cloud_group_name = "sheer lights"

        interp = get_interpreter(Mode.rave, movers, self.args)
        interp.step(self.frame, self.scheme)

        focus_values = {m.get_focus() for m in movers}
        prism_states = {m.get_prism()[0] for m in movers}
        assert len(focus_values) > 1, (
            f"Expected varied focus across sheer movers, got {focus_values}"
        )
        assert prism_states == {True, False}, (
            f"Expected both prism-on and prism-off across sheer movers, got {prism_states}"
        )

    def test_composite_interpreter_exposes_children_with_their_own_groups(self):
        """CompositeInterpreter.children must each carry the matched sub-group.

        The DMX lighting-tree printer relies on ``children`` (not the flat parent
        group + the merged ``__str__``) so each partition prints its own row.
        """
        from parrot.director.mode_dispatch import CompositeInterpreter
        from parrot.fixtures.chauvet.intimidator_hybrid_140sr import (
            ChauvetIntimidatorHybrid140SR_19Ch,
        )
        from parrot.fixtures.chauvet.rogue_beam_r2 import ChauvetRogueBeamR2

        sheer = ChauvetIntimidatorHybrid140SR_19Ch(1)
        sheer.cloud_group_name = "sheer lights"
        rogue = ChauvetRogueBeamR2(20)
        rogue.cloud_group_name = None
        mirror = Mirrorball(40)

        interp = get_interpreter(Mode.rave_gentle, [sheer, rogue, mirror], self.args)
        assert isinstance(interp, CompositeInterpreter), (
            "rave_gentle with mixed fixture classes should partition into a composite"
        )
        children = interp.children
        # Every child's group must be a strict subset of the parent patch, and
        # the union (by identity) must cover every fixture exactly once.
        seen: list[int] = []
        for child in children:
            for f in child.group:
                seen.append(id(f))
            assert len(child.group) >= 1, "Composite children should never be empty"
            assert len(child.group) < 3, (
                f"Each child should be one partition, not the whole patch: {child.group}"
            )
        assert sorted(seen) == sorted([id(sheer), id(rogue), id(mirror)])

    def test_mirrorball_resolves_before_par_not_test_rig_cycle(self):
        """Mirrorball subclasses Par; mode must use the Mirrorball row, not Par animations."""
        mb = Mirrorball(88)
        chill = get_interpreter(Mode.chill, [mb], self.args)
        self.assertIsInstance(chill.interpreter, Dimmer0)
        chill.step(self.frame, self.scheme)
        self.assertEqual(mb.get_dimmer(), 0)

        mb2 = Mirrorball(89)
        test_interp = get_interpreter(Mode.test, [mb2], self.args)
        test_interp.step(self.frame, self.scheme)
        self.assertEqual(mb2.get_dimmer(), 255)


if __name__ == "__main__":
    unittest.main()
