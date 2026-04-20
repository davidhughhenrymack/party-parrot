"""Tests for 2s interpretation blending (outgoing primary + incoming + lerp output)."""

import os
import tempfile
import shutil
import unittest

from parrot.director.director import Director
from parrot.director.frame import Frame, FrameSignal
from parrot.director import director as director_mod
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


if __name__ == "__main__":
    unittest.main()
