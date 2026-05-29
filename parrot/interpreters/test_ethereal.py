"""DB-backed ethereal mode coverage."""

from parrot.director.animation_registry import animation
from parrot.director.color_scheme import ColorScheme
from parrot.director.frame import Frame, FrameSignal
from parrot.director.mode import Mode
from parrot.director.mode_dispatch import get_interpreter
from parrot.fixtures.chauvet.rogue_hybrid_rh1 import ChauvetRogueHybridRH1_20Ch
from parrot.interpreters.base import InterpreterArgs
from parrot.utils.colour import Color
from parrot_cloud.domain import (
    LightingModeSpec,
    VenueAnimationAssignmentSpec,
    VenueSnapshot,
    VenueSummary,
    VideoWallSpec,
)


def _frame() -> Frame:
    fv = {s: 0.0 for s in FrameSignal}
    ts = {s.name: [0.0] * 50 for s in FrameSignal}
    f = Frame(fv, ts)
    f.time = 100.0
    return f


def _snapshot(
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
                key="ethereal",
                label="Ethereal",
                order_index=0,
            ),
        ),
        animation_assignments=assignments,
    )


def test_ethereal_uses_db_assignments_for_group_scoped_movers() -> None:
    sheer = ChauvetRogueHybridRH1_20Ch(1)
    sheer.cloud_group_name = "sheer lights"
    other = ChauvetRogueHybridRH1_20Ch(20)
    other.cloud_group_name = "other"
    snapshot = _snapshot(
        (
            VenueAnimationAssignmentSpec(
                id="assignment",
                venue_id="venue",
                lighting_mode_id="mode",
                lighting_mode_key="ethereal",
                fixture_group_name="sheer lights",
                fixture_type="moving_head",
                order_index=0,
                animation_spec=animation("Dimmer255"),
            ),
        )
    )

    interp = get_interpreter(
        Mode.ethereal,
        [sheer, other],
        InterpreterArgs(True),
        snapshot,
    )
    interp.step(_frame(), ColorScheme(Color("red"), Color("blue"), Color("white")))

    assert sheer.get_dimmer() == 255
    assert other.get_dimmer() == 0
