import pytest
from unittest.mock import Mock, patch, MagicMock
from parrot.gl_display_mode import EditorDisplayMode
from parrot.state import State
from parrot.director.mode import Mode
from parrot.director.themes import themes
from parrot_cloud.domain import (
    FixtureSpec,
    SceneObjectSpec,
    VenueSnapshot,
    VenueSummary,
    VideoWallSpec,
)


class TestState:
    def test_state_initialization(self):
        """Test that State initializes with correct default values."""
        state = State()

        assert state.mode == Mode.chill  # Default mode
        assert state.hype == 30
        assert state.theme == themes[0]
        assert state.hype_limiter is False
        assert state.show_waveform is True
        assert state.editor_display_mode == EditorDisplayMode.DMX_HEATMAP
        assert state.show_fixture_mode is False
        assert hasattr(state, "events")
        assert hasattr(state, "signal_states")

    def test_set_mode(self):
        """Test setting mode triggers events."""
        state = State()
        mock_handler = Mock()
        state.events.on_mode_change += mock_handler

        state.set_mode(Mode.rave)

        assert state.mode == Mode.rave
        mock_handler.assert_called_once_with(Mode.rave)

    def test_set_mode_same_value_no_event(self):
        """Test setting same mode doesn't trigger events."""
        state = State()
        state.set_mode(Mode.rave)

        mock_handler = Mock()
        state.events.on_mode_change += mock_handler

        state.set_mode(Mode.rave)  # Same value

        mock_handler.assert_not_called()

    def test_set_mode_thread_safe(self):
        """Test thread-safe mode setting."""
        state = State()

        state.set_mode_thread_safe(Mode.chill)

        assert state.mode == Mode.chill

    def test_set_hype(self):
        """Test setting hype value triggers events."""
        state = State()
        mock_handler = Mock()
        state.events.on_hype_change += mock_handler

        state.set_hype(75.0)

        assert state.hype == 75.0
        mock_handler.assert_called_once_with(75.0)

    def test_set_theme(self):
        """Test setting theme triggers events."""
        state = State()
        mock_handler = Mock()
        state.events.on_theme_change += mock_handler

        new_theme = themes[1] if len(themes) > 1 else themes[0]
        state.set_theme(new_theme)

        assert state.theme == new_theme
        mock_handler.assert_called_once_with(new_theme)

    def test_set_hype_limiter(self):
        """Test setting hype limiter triggers events."""
        state = State()
        mock_handler = Mock()
        state.events.on_hype_limiter_change += mock_handler

        state.set_hype_limiter(True)

        assert state.hype_limiter is True
        mock_handler.assert_called_once_with(True)

    def test_set_show_waveform(self):
        """Test setting show waveform triggers events."""
        state = State()
        mock_handler = Mock()
        state.events.on_show_waveform_change += mock_handler

        state.set_show_waveform(False)

        assert state.show_waveform is False
        mock_handler.assert_called_once_with(False)

    def test_set_show_fixture_mode(self):
        """Test setting show fixture mode triggers events."""
        state = State()
        mock_handler = Mock()
        state.events.on_show_fixture_mode_change += mock_handler

        state.set_show_fixture_mode(True)

        assert state.show_fixture_mode is True
        mock_handler.assert_called_once_with(True)

    def test_cycle_editor_display_mode(self):
        state = State()
        assert state.editor_display_mode == EditorDisplayMode.DMX_HEATMAP
        state.cycle_editor_display_mode()
        assert state.editor_display_mode == EditorDisplayMode.VJ
        state.cycle_editor_display_mode()
        assert state.editor_display_mode == EditorDisplayMode.FIXTURE_SCENE
        state.cycle_editor_display_mode()
        assert state.editor_display_mode == EditorDisplayMode.DMX_HEATMAP

    def test_set_effect_thread_safe_presses_and_releases(self):
        """Remote control taps fire the signal then release it so it doesn't stick on."""
        import time

        from parrot.director.frame import FrameSignal

        state = State()
        state.signal_states.set_signal = Mock()

        state.set_effect_thread_safe("strobe")

        state.signal_states.set_signal.assert_called_once_with(FrameSignal.strobe, 1.0)

        # Wait out the auto-release timer (currently 0.35s).
        deadline = time.time() + 1.0
        while time.time() < deadline and state.signal_states.set_signal.call_count < 2:
            time.sleep(0.05)

        assert state.signal_states.set_signal.call_args_list[-1] == (
            (FrameSignal.strobe, 0.0),
            {},
        )

    def test_process_gui_updates_empty_queue(self):
        """Test processing GUI updates with empty queue."""
        state = State()
        # Should not raise an exception
        state.process_gui_updates()

    def test_runtime_shift_fires_registered_event_handler(self):
        """Remote shift messages must reach subscribers via process_gui_updates."""
        state = State()
        lighting_handler = Mock()
        color_handler = Mock()
        vj_handler = Mock()
        state.events.on_shift_lighting_only_request += lighting_handler
        state.events.on_shift_color_scheme_request += color_handler
        state.events.on_shift_vj_only_request += vj_handler

        state.queue_runtime_shift("lighting_only")
        state.queue_runtime_shift("color_scheme")
        state.queue_runtime_shift("vj_only")
        state.process_gui_updates()

        lighting_handler.assert_called_once_with()
        color_handler.assert_called_once_with()
        vj_handler.assert_called_once_with()

    def test_process_gui_updates_runtime_venues_notifies_listeners(self):
        state = State()
        handler = Mock()
        state.events.on_available_venues_change += handler
        new_venues = [
            VenueSummary(
                id="v-new",
                slug="new",
                name="New Venue",
                archived=False,
                active=False,
                revision=1,
            )
        ]
        state._gui_update_queue.put(("runtime_venues", new_venues))
        state.process_gui_updates()
        assert state.available_venues == new_venues
        handler.assert_called_once_with(new_venues)

    def test_runtime_scene_update_does_not_switch_fixture_mode(self):
        state = State()
        venue_change_handler = Mock()
        runtime_scene_handler = Mock()
        state.events.on_venue_change += venue_change_handler
        state.events.on_runtime_scene_change += runtime_scene_handler

        initial_snapshot = VenueSnapshot(
            summary=VenueSummary(
                id="venue-1",
                slug="demo",
                name="Demo Venue",
                archived=False,
                active=True,
                revision=1,
            ),
            floor_width=20.0,
            floor_depth=15.0,
            floor_height=10.0,
            video_wall=VideoWallSpec(
                x=10.0,
                y=1.0,
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
                    x=1.0,
                    y=2.0,
                    z=3.0,
                ),
            ),
            scene_objects=(
                SceneObjectSpec(
                    id="floor",
                    kind="floor",
                    x=10.0,
                    y=7.5,
                    z=0.0,
                    width=20.0,
                    height=15.0,
                    depth=0.08,
                ),
            ),
        )
        updated_snapshot = VenueSnapshot(
            summary=VenueSummary(
                id="venue-1",
                slug="demo",
                name="Demo Venue",
                archived=False,
                active=True,
                revision=2,
            ),
            floor_width=20.0,
            floor_depth=15.0,
            floor_height=10.0,
            video_wall=VideoWallSpec(
                x=10.0,
                y=1.0,
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
                    x=4.0,
                    y=5.0,
                    z=6.0,
                ),
            ),
            scene_objects=(
                SceneObjectSpec(
                    id="floor",
                    kind="floor",
                    x=10.0,
                    y=7.5,
                    z=0.0,
                    width=20.0,
                    height=15.0,
                    depth=0.08,
                ),
            ),
        )

        state._apply_runtime_snapshot(initial_snapshot)
        state.set_show_fixture_mode(True)
        venue_change_handler.reset_mock()
        runtime_scene_handler.reset_mock()

        state._apply_runtime_snapshot(updated_snapshot)

        assert state.show_fixture_mode is True
        venue_change_handler.assert_not_called()
        runtime_scene_handler.assert_called_once_with(updated_snapshot)

    def test_runtime_scene_update_preserves_fixture_instances(self):
        state = State()
        initial_snapshot = VenueSnapshot(
            summary=VenueSummary(
                id="venue-1",
                slug="demo",
                name="Demo Venue",
                archived=False,
                active=True,
                revision=1,
            ),
            floor_width=20.0,
            floor_depth=15.0,
            floor_height=10.0,
            video_wall=VideoWallSpec(
                x=10.0,
                y=1.0,
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
                    x=1.0,
                    y=2.0,
                    z=3.0,
                ),
            ),
            scene_objects=(
                SceneObjectSpec(
                    id="floor",
                    kind="floor",
                    x=10.0,
                    y=7.5,
                    z=0.0,
                    width=20.0,
                    height=15.0,
                    depth=0.08,
                ),
            ),
        )
        updated_snapshot = VenueSnapshot(
            summary=VenueSummary(
                id="venue-1",
                slug="demo",
                name="Demo Venue",
                archived=False,
                active=True,
                revision=2,
            ),
            floor_width=20.0,
            floor_depth=15.0,
            floor_height=10.0,
            video_wall=VideoWallSpec(
                x=10.0,
                y=1.0,
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
                    x=9.0,
                    y=8.0,
                    z=7.0,
                ),
            ),
            scene_objects=(
                SceneObjectSpec(
                    id="floor",
                    kind="floor",
                    x=10.0,
                    y=7.5,
                    z=0.0,
                    width=20.0,
                    height=15.0,
                    depth=0.08,
                ),
            ),
        )

        state._apply_runtime_snapshot(initial_snapshot)
        original_fixture = state.runtime_patch[0]

        state._apply_runtime_snapshot(updated_snapshot)

        assert state.runtime_patch[0] is original_fixture
        assert original_fixture.x == 9.0
        assert original_fixture.y == 8.0
        assert original_fixture.z == 7.0

    def test_runtime_scene_update_applies_pan_tilt_range_live(self):
        """Editing a moving head's pan/tilt range in the venue editor must
        take effect on the live runtime fixture on the next snapshot, without
        requiring a scene rebuild (which would cost a re-sync / visual reset).
        """
        state = State()

        def make_snapshot(revision: int, options: dict):
            return VenueSnapshot(
                summary=VenueSummary(
                    id="venue-1",
                    slug="demo",
                    name="Demo Venue",
                    archived=False,
                    active=True,
                    revision=revision,
                ),
                floor_width=20.0,
                floor_depth=15.0,
                floor_height=10.0,
                video_wall=VideoWallSpec(
                    x=10.0, y=1.0, z=3.0,
                    width=10.0, height=6.0, depth=0.25,
                    locked=False,
                ),
                fixtures=(
                    FixtureSpec(
                        id="spot-1",
                        fixture_type="chauvet_spot_160",
                        address=10,
                        universe="default",
                        x=1.0, y=2.0, z=3.0,
                        options=options,
                    ),
                ),
                scene_objects=(),
            )

        initial = make_snapshot(
            1,
            {"pan_lower": 360, "pan_upper": 540, "tilt_lower": 0, "tilt_upper": 90},
        )
        # Simulate the user dragging the pan/tilt range panel to the "Full"
        # preset: full mechanical sweep.
        updated = make_snapshot(
            2,
            {"pan_lower": 0, "pan_upper": 540, "tilt_lower": 0, "tilt_upper": 270},
        )

        state._apply_runtime_snapshot(initial)
        live_fixture = state.runtime_patch[0]
        initial_tilt_upper_dmx = live_fixture.tilt_upper

        state._apply_runtime_snapshot(updated)

        # Same fixture instance (in-place update, no scene rebuild).
        assert state.runtime_patch[0] is live_fixture
        # tilt_upper is stored in DMX-unit space (deg / 270 * 255). After the
        # update the full 270° sweep should map to the full DMX range (255).
        assert live_fixture.tilt_upper == pytest.approx(255.0)
        assert live_fixture.tilt_upper != pytest.approx(initial_tilt_upper_dmx)
        assert live_fixture.pan_lower == pytest.approx(0.0)
        assert live_fixture.pan_upper == pytest.approx(255.0)
