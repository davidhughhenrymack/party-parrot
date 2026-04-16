from parrot.gl_display_mode import EditorDisplayMode
from parrot.state import State
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
