"""Tests for 2s interpretation blending (outgoing primary + incoming + lerp output)."""

import os
import tempfile
import shutil
import unittest

from parrot.director.director import Director
from parrot.director.frame import Frame, FrameSignal
from parrot.director.mode import Mode, mode_key
from parrot.director import director as director_mod
from parrot.interpreters.base import InterpreterBase
from parrot.fixtures.led_par import ParRGB
from parrot.state import State
from parrot.utils.colour import Color
from parrot_cloud.domain import (
    LightingModeSpec,
    VenueSnapshot,
    VenueSummary,
    VideoWallSpec,
)


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
            (Mode.blackout, 0.5),
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

    def test_blend_duration_uses_runtime_venue_lighting_mode_entry_seconds(self):
        self.state._runtime_venue_snapshot = VenueSnapshot(
            summary=VenueSummary(
                id="venue",
                slug="venue",
                name="Venue",
                archived=False,
                active=True,
                revision=1,
            ),
            floor_width=20.0,
            floor_depth=15.0,
            floor_height=10.0,
            video_wall=VideoWallSpec(
                x=0.0,
                y=0.0,
                z=0.0,
                width=10.0,
                height=6.0,
                depth=0.25,
                locked=False,
            ),
            fixtures=(),
            lighting_modes=(
                LightingModeSpec(
                    id="mode",
                    venue_id="venue",
                    key="rave",
                    label="Rave",
                    order_index=0,
                    entry_seconds=1.25,
                ),
            ),
        )
        self.state._mode = Mode.rave

        self.director._start_interpretation_blend(
            [0],
            {0: self.director._default_interpreter_args_for_bucket_index(0)},
        )

        self.assertEqual(self.director._interpretation_blend.duration_seconds, 1.25)

    def test_mode_change_blend_duration_uses_destination_mode_entry_seconds(self):
        self.state._runtime_venue_snapshot = VenueSnapshot(
            summary=VenueSummary(
                id="venue",
                slug="venue",
                name="Venue",
                archived=False,
                active=True,
                revision=1,
            ),
            floor_width=20.0,
            floor_depth=15.0,
            floor_height=10.0,
            video_wall=VideoWallSpec(
                x=0.0,
                y=0.0,
                z=0.0,
                width=10.0,
                height=6.0,
                depth=0.25,
                locked=False,
            ),
            fixtures=(),
            lighting_modes=(
                LightingModeSpec(
                    id="chill",
                    venue_id="venue",
                    key="chill",
                    label="Chill",
                    order_index=0,
                    entry_seconds=9.0,
                ),
                LightingModeSpec(
                    id="rave",
                    venue_id="venue",
                    key="rave",
                    label="Rave",
                    order_index=1,
                    entry_seconds=1.25,
                ),
            ),
        )
        self.state._mode = Mode.chill

        self.director.on_mode_change(Mode.rave)

        self.assertEqual(self.director._interpretation_blend.duration_seconds, 1.25)

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

        tree = self.director.print_lighting_tree(mode_key(self.state.mode))

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
