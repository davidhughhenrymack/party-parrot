"""Tests for 2s interpretation blending (outgoing primary + incoming + lerp output)."""

import os
import tempfile
import shutil
import unittest

from parrot.director.director import Director
from parrot.director.frame import Frame, FrameSignal
from parrot.director.mode import Mode
from parrot.director import director as director_mod
from parrot.interpreters.base import InterpreterBase
from parrot.fixtures.led_par import ParRGB
from parrot.state import State
from parrot.utils.colour import Color


class TestInterpretationBlend(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)
        self._prev_blend = director_mod.INTERPRETATION_BLEND_SECONDS
        director_mod.INTERPRETATION_BLEND_SECONDS = 0.02

        self.state = State()
        self.par = ParRGB(10)
        self.par.cloud_spec_id = "spec-par-1"
        self.state._runtime_patch = [self.par]
        self.state._runtime_manual_group = None
        self.director = Director(self.state)

    def tearDown(self):
        director_mod.INTERPRETATION_BLEND_SECONDS = self._prev_blend
        os.chdir(self.original_cwd)
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_resolve_output_during_blend_uses_lerp_fixture(self):
        self.director._start_interpretation_blend(
            [0],
            {0: self.director._default_interpreter_args_for_bucket_index(0)},
        )
        b = self.director._interpretation_blend
        self.assertIsNotNone(b)
        out = self.director.resolve_output_fixture(self.par)
        self.assertIs(out, b.lerp_fixtures[0][0])
        overrides = self.director.output_fixture_overrides_by_spec_id()
        self.assertEqual(overrides["spec-par-1"], b.lerp_fixtures[0][0])

    def test_promote_replaces_runtime_patch_and_clears_blend(self):
        self.director._start_interpretation_blend(
            [0],
            {0: self.director._default_interpreter_args_for_bucket_index(0)},
        )
        incoming = self.director._interpretation_blend.incoming_fixtures[0][0]
        scheme = self.director.scheme.render()
        frame = Frame({s: 0.0 for s in FrameSignal})
        self.director._finish_interpretation_blend(frame, scheme)
        self.assertIsNone(self.director._interpretation_blend)
        self.assertIs(self.state.runtime_patch[0], incoming)
        self.assertIs(self.director.fixture_groups[0][0], incoming)

    def test_lerp_into_par_rgb_midpoint(self):
        a = ParRGB(1)
        b = ParRGB(2)
        a.set_dimmer(0)
        a.set_color(Color("black"))
        b.set_dimmer(100)
        b.set_color(Color("white"))
        out = ParRGB(3)
        out.lerp_into(a, b, 0.5)
        self.assertAlmostEqual(out.get_dimmer(), 50.0, places=3)

    def test_blend_duration_is_selected_by_target_mode(self):
        cases = [
            (Mode.ethereal, 3.0),
            (Mode.chill, 3.0),
            (Mode.rave, 0.5),
            (Mode.stroby, 0.1),
            (Mode.blackout, director_mod.INTERPRETATION_BLEND_SECONDS),
        ]

        for mode, expected in cases:
            with self.subTest(mode=mode):
                self.director._interpretation_blend = None
                self.state._mode = mode
                self.director._start_interpretation_blend(
                    [0],
                    {0: self.director._default_interpreter_args_for_bucket_index(0)},
                )
                self.assertEqual(
                    self.director._interpretation_blend.duration_seconds,
                    expected,
                )

    def test_lighting_tree_prints_blend_destination(self):
        self.director.interpreters[0] = _NamedInterpreter(
            self.director.fixture_groups[0],
            self.director._default_interpreter_args_for_bucket_index(0),
            "CURRENT",
        )
        self.director._start_interpretation_blend(
            [0],
            {0: self.director._default_interpreter_args_for_bucket_index(0)},
        )
        b = self.director._interpretation_blend
        self.assertIsNotNone(b)
        b.incoming_interpreters[0] = _NamedInterpreter(
            b.incoming_fixtures[0],
            self.director._default_interpreter_args_for_bucket_index(0),
            "DESTINATION",
        )

        tree = self.director.print_lighting_tree(self.state.mode.name)

        self.assertIn("DESTINATION", tree)
        self.assertNotIn("CURRENT", tree)


class _NamedInterpreter(InterpreterBase):
    def __init__(self, group, args, name: str):
        super().__init__(group, args)
        self._name = name

    def __str__(self) -> str:
        return self._name


if __name__ == "__main__":
    unittest.main()
