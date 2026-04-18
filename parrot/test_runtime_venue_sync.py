from parrot.director.director import Director
from parrot.gl_display_mode import EditorDisplayMode
from parrot.state import State
from parrot.vj.nodes.fixture_visualization import FixtureVisualization
from parrot.vj.vj_director import VJDirector
from parrot_cloud.domain import (
    ControlState,
    FixtureSpec,
    RuntimeBootstrap,
    VenueSnapshot,
    VenueSummary,
    VideoWallSpec,
)


def test_state_applies_runtime_bootstrap():
    state = State()
    bootstrap = RuntimeBootstrap(
        venues=(
            VenueSummary(
                id="venue-1",
                slug="demo",
                name="Demo Venue",
                archived=False,
                active=True,
                revision=3,
            ),
        ),
        active_venue=VenueSnapshot(
            summary=VenueSummary(
                id="venue-1",
                slug="demo",
                name="Demo Venue",
                archived=False,
                active=True,
                revision=3,
            ),
            floor_width=20.0,
            floor_depth=15.0,
            floor_height=10.0,
            video_wall=VideoWallSpec(
                x=1.0,
                y=2.0,
                z=3.0,
                width=10.0,
                height=6.0,
                depth=0.25,
                locked=False,
            ),
            fixtures=(
                FixtureSpec(
                    id="fixture-1",
                    fixture_type="par_rgb",
                    address=10,
                    universe="default",
                    x=20.0,
                    y=30.0,
                    z=4.0,
                ),
            ),
        ),
        control_state=ControlState(
            mode="rave",
            vj_mode="zr_full_rave",
            theme_name="Rave",
            active_venue_id="venue-1",
            display_mode="dmx_heatmap",
            manual_dimmer=0.4,
            hype_limiter=False,
            show_waveform=True,
        ),
    )

    state.apply_runtime_bootstrap(bootstrap)

    assert state.venue.name == "Demo Venue"
    assert state.mode.name == "rave"
    assert state.runtime_patch is not None
    assert len(state.runtime_patch) == 1
    assert state.runtime_patch[0].address == 10
    assert state.manual_dimmer == 0.4
    assert state.editor_display_mode == EditorDisplayMode.DMX_HEATMAP


def test_room_layout_uses_snapshot_floor_when_scene_objects_empty():
    """Desktop 3D floor must match venue snapshot fields from the central DB."""
    bootstrap = RuntimeBootstrap(
        venues=(
            VenueSummary(
                id="venue-1",
                slug="demo",
                name="Demo Venue",
                archived=False,
                active=True,
                revision=3,
            ),
        ),
        active_venue=VenueSnapshot(
            summary=VenueSummary(
                id="venue-1",
                slug="demo",
                name="Demo Venue",
                archived=False,
                active=True,
                revision=3,
            ),
            floor_width=24.5,
            floor_depth=18.25,
            floor_height=9.0,
            video_wall=VideoWallSpec(
                x=0.0,
                y=3.0,
                z=-4.5,
                width=10.0,
                height=6.0,
                depth=0.25,
                locked=False,
            ),
            fixtures=(
                FixtureSpec(
                    id="fixture-1",
                    fixture_type="par_rgb",
                    address=10,
                    universe="default",
                    x=20.0,
                    y=30.0,
                    z=4.0,
                ),
            ),
            scene_objects=(),
        ),
        control_state=ControlState(
            mode="rave",
            vj_mode="zr_full_rave",
            theme_name="Rave",
            active_venue_id="venue-1",
            display_mode="dmx_heatmap",
            manual_dimmer=0.4,
            hype_limiter=False,
            show_waveform=True,
        ),
    )

    state = State()
    state.apply_runtime_bootstrap(bootstrap)
    vj_director = VJDirector(state)
    director = Director(state, vj_director)
    fx = FixtureVisualization(state, director.position_manager, vj_director)
    layout = fx._build_room_scene_layout()

    assert layout["floor"]["width"] == 24.5
    assert layout["floor"]["depth"] == 18.25
    assert layout["floor"]["room_height"] == 9.0
    assert layout["video_wall"]["width"] == 10.0
