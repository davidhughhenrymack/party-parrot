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
        """Rave picks one focus and one prism state for the whole sheer group.

        Per-group randomize (not per-fixture) means all sheer movers share the
        chosen focus/prism, and rebuilding enough times visits both options in
        each randomize call — that proves the DSL is actually picking, not frozen.
        """
        import random as _random
        from parrot.fixtures.chauvet.intimidator_hybrid_140sr import (
            ChauvetIntimidatorHybrid140SR_19Ch,
        )

        focus_picks: set[float] = set()
        prism_picks: set[bool] = set()

        for seed in range(40):
            _random.seed(seed)
            movers = [
                ChauvetIntimidatorHybrid140SR_19Ch(1 + i * 20) for i in range(6)
            ]
            for m in movers:
                m.cloud_group_name = "sheer lights"

            interp = get_interpreter(Mode.rave, movers, self.args)
            interp.step(self.frame, self.scheme)

            focus_values = {m.get_focus() for m in movers}
            prism_states = {m.get_prism()[0] for m in movers}

            # Group-wise randomize: every mover in the group must agree.
            assert len(focus_values) == 1, (
                f"seed={seed}: expected one shared focus across the group, got {focus_values}"
            )
            assert len(prism_states) == 1, (
                f"seed={seed}: expected one shared prism state across the group, got {prism_states}"
            )

            (focus,) = focus_values
            (prism_on,) = prism_states
            assert focus in (0.0, 1.0), f"seed={seed}: unexpected focus {focus}"
            focus_picks.add(focus)
            prism_picks.add(prism_on)

        assert focus_picks == {0.0, 1.0}, (
            f"randomize(FocusBig, FocusSmall) should visit both options; got {focus_picks}"
        )
        assert prism_picks == {True, False}, (
            f"randomize(RotatePrism, PrismOff) should visit both options; got {prism_picks}"
        )

    def test_rave_sheer_lights_active_roughly_thirty_percent_of_reshuffles(self):
        """Rave sheer movers should be dark ~70% of the time.

        The outer matcher wraps the full combo in a 30/70 ``weighted_randomize``
        against ``Dimmer0`` so the sheer lights feel like an occasional accent,
        not a constant presence. We sample many seeds and assert the empirical
        activation rate sits in a band around 30% — wide enough to absorb
        normal variance but tight enough to catch a regression that flips the
        weights, drops the gate entirely, or silences the sheers forever.
        """
        import random as _random
        from parrot.fixtures.chauvet.intimidator_hybrid_140sr import (
            ChauvetIntimidatorHybrid140SR_19Ch,
        )

        trials = 400
        active = 0
        for seed in range(trials):
            _random.seed(seed)
            movers = [
                ChauvetIntimidatorHybrid140SR_19Ch(1 + i * 20) for i in range(4)
            ]
            for m in movers:
                m.cloud_group_name = "sheer lights"

            interp = get_interpreter(Mode.rave, movers, self.args)
            # Step several frames so any combo that needs a few ticks to lift
            # the dimmer (latched fades, chases, etc.) actually drives output.
            for _ in range(8):
                interp.step(self.frame, self.scheme)

            # "Active" == at least one mover in the group lit up this pass.
            # Dimmer0 keeps every fixture at 0; the combo lifts at least one.
            if any(m.get_dimmer() > 0 for m in movers):
                active += 1

        rate = active / trials
        # 30/70 weighted pick → expected mean 0.30, stdev ≈ sqrt(0.21/400) ≈ 0.023.
        # Band [0.18, 0.42] is ~5σ — generous enough to be non-flaky, tight
        # enough to fail if someone sets the weights to (50,50) or (10,90).
        assert 0.18 <= rate <= 0.42, (
            f"sheer-lights activation rate should be ~30%, got {rate:.2%} "
            f"({active}/{trials})"
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
