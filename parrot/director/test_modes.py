import unittest

from parrot.director.animation_registry import animation
from parrot.director.frame import Frame, FrameSignal
from parrot.director.mode_dispatch import get_interpreter
from parrot.director.mode import Mode
from parrot.interpreters.base import InterpreterArgs
from parrot.fixtures.led_par import ParRGB
from parrot.interpreters.dimmer import Dimmer0
from parrot.director.color_scheme import ColorScheme
from parrot.utils.colour import Color
from parrot_cloud.domain import (
    LightingModeSpec,
    VenueAnimationAssignmentSpec,
    VenueSnapshot,
    VenueSummary,
    VideoWallSpec,
)


def _snapshot(
    key: str,
    assignments: tuple[VenueAnimationAssignmentSpec, ...],
) -> VenueSnapshot:
    return VenueSnapshot(
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
                key=key,
                label=key.title(),
                order_index=0,
            ),
        ),
        animation_assignments=assignments,
    )


class TestModes(unittest.TestCase):
    def setUp(self):
        # Create a test frame with some activity
        frame_values = {
            FrameSignal.freq_all: 0.8,  # High value to trigger beat detection
            FrameSignal.freq_high: 0.8,  # High value to trigger beat detection
            FrameSignal.freq_low: 0.8,  # High value to trigger beat detection
            FrameSignal.sustained_low: 0.1,
            FrameSignal.sustained_high: 0.8,  # High value to trigger effects
        }
        timeseries = {
            FrameSignal.freq_all.name: [0.8] * 200,
            FrameSignal.freq_high.name: [0.8] * 200,
            FrameSignal.freq_low.name: [0.8] * 200,
            FrameSignal.sustained_low.name: [0.1] * 200,
            FrameSignal.sustained_high.name: [0.8] * 200,
        }
        self.frame = Frame(frame_values, timeseries)
        self.args = InterpreterArgs(True)

        # Create a test color scheme
        self.scheme = ColorScheme(
            Color("red"), Color("blue"), Color("white")  # fg  # bg  # bg_contrast
        )

    def test_non_blackout_modes_without_snapshot_fall_back_to_dimmer_zero(self):
        par = ParRGB(1)
        interpreter = get_interpreter(Mode.chill, [par], self.args)

        self.assertIsInstance(interpreter, Dimmer0)
        interpreter.step(self.frame, self.scheme)
        self.assertEqual(par.get_dimmer(), 0)

    def test_blackout_is_hardwired_to_dimmer_zero(self):
        par = ParRGB(1)
        interpreter = get_interpreter(Mode.blackout, [par], self.args)

        self.assertIsInstance(interpreter, Dimmer0)
        interpreter.step(self.frame, self.scheme)
        self.assertEqual(par.get_dimmer(), 0)

    def test_db_assignment_drives_matching_mode(self):
        par = ParRGB(1)
        snapshot = _snapshot(
            "chill",
            (
                VenueAnimationAssignmentSpec(
                    id="assignment",
                    venue_id="venue",
                    lighting_mode_id="mode",
                    lighting_mode_key="chill",
                    fixture_group_name=None,
                    fixture_type="par",
                    order_index=0,
                    animation_spec=animation("Dimmer255"),
                ),
            ),
        )

        interpreter = get_interpreter(Mode.chill, [par], self.args, snapshot)
        interpreter.step(self.frame, self.scheme)

        self.assertEqual(par.get_dimmer(), 255)

    def test_composite_interpreter_exposes_children_with_their_own_groups(self):
        """CompositeInterpreter.children must each carry the matched sub-group.

        The DMX lighting-tree printer relies on ``children`` (not the flat parent
        group + the merged ``__str__``) so each partition prints its own row.
        """
        from parrot.director.mode_dispatch import CompositeInterpreter
        from parrot.fixtures.chauvet.rogue_beam_r2 import ChauvetRogueBeamR2X

        front = ChauvetRogueBeamR2X(1)
        front.cloud_group_name = "front"
        rear = ChauvetRogueBeamR2X(20)
        rear.cloud_group_name = "rear"
        snapshot = _snapshot(
            "rave",
            (
                VenueAnimationAssignmentSpec(
                    id="front",
                    venue_id="venue",
                    lighting_mode_id="mode",
                    lighting_mode_key="rave",
                    fixture_group_name="front",
                    fixture_type="moving_head",
                    order_index=0,
                    animation_spec=animation("Dimmer255"),
                ),
                VenueAnimationAssignmentSpec(
                    id="rear",
                    venue_id="venue",
                    lighting_mode_id="mode",
                    lighting_mode_key="rave",
                    fixture_group_name="rear",
                    fixture_type="moving_head",
                    order_index=1,
                    animation_spec=animation("Dimmer0"),
                ),
            ),
        )

        interp = get_interpreter(Mode.rave, [front, rear], self.args, snapshot)

        self.assertIsInstance(interp, CompositeInterpreter)
        self.assertEqual([child.group for child in interp.children], [[front], [rear]])


if __name__ == "__main__":
    unittest.main()
