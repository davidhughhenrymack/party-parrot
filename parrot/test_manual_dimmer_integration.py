"""Integration tests for manual dimmer control - keyboard -> fixture -> renderer"""

import pytest
from unittest.mock import Mock, MagicMock
import pyglet
import moderngl

from parrot.keyboard_handler import KeyboardHandler
from parrot.director.director import Director
from parrot.director.frame import Frame, FrameSignal
from parrot.director.signal_states import SignalStates
from parrot.director.color_scheme import ColorScheme
from parrot.state import State
from parrot.utils.overlay_ui import OverlayUI
from parrot.fixtures.base import FixtureBase, ManualGroup
from parrot.vj.renderers.bulb import BulbRenderer
from parrot.vj.renderers.room_3d import Room3DRenderer
from parrot.patch_bay import venues


class TestManualDimmerIntegration:
    """Integration tests for manual dimmer control flow"""

    def setup_method(self):
        """Setup test fixtures"""
        # Create real fixtures for manual group
        self.manual_fixture_1 = FixtureBase(1, "Manual Spot 1", 1)
        self.manual_fixture_2 = FixtureBase(2, "Manual Spot 2", 1)

        # Create manual group
        self.manual_group = ManualGroup(
            [self.manual_fixture_1, self.manual_fixture_2], "Test Manual Group"
        )

        # Create state and prevent it from writing to state.json during tests
        self.state = State()
        self.state.save_state = Mock()  # Mock save_state to prevent file writes
        self.state.set_venue(venues.dmack)  # Use a real venue

        # Create mocked components
        self.director = Mock(spec=Director)
        self.overlay = Mock(spec=OverlayUI)
        self.signal_states = Mock(spec=SignalStates)

        # Create keyboard handler
        self.handler = KeyboardHandler(
            self.director, self.overlay, self.signal_states, self.state
        )

    def test_keyboard_m_starts_fade_up(self):
        """Test that M key starts fading up manual dimmer"""
        # Press M key
        result = self.handler.on_key_press(pyglet.window.key.M, 0)

        assert result is True
        assert self.handler.manual_fade_direction == 1

        # Simulate 0.5 seconds passing (should fade to full brightness at speed 2.0)
        self.handler.update_manual_dimmer(0.5)
        assert self.state.manual_dimmer == 1.0

    def test_keyboard_k_starts_fade_down(self):
        """Test that K key starts fading down manual dimmer"""
        # First set to 1.0
        self.state.set_manual_dimmer(1.0)
        assert self.state.manual_dimmer == 1.0

        # Press K key
        result = self.handler.on_key_press(pyglet.window.key.K, 0)

        assert result is True
        assert self.handler.manual_fade_direction == -1

        # Simulate 0.5 seconds passing (should fade to off at speed 2.0)
        self.handler.update_manual_dimmer(0.5)
        assert self.state.manual_dimmer == 0.0

    def test_manual_group_applies_dimmer_to_fixtures(self):
        """Test that ManualGroup.set_manual_dimmer properly sets fixture dimmer values"""
        # Initially fixtures should have dimmer_value = 0
        assert self.manual_fixture_1.dimmer_value == 0
        assert self.manual_fixture_2.dimmer_value == 0

        # Set manual dimmer to full (1.0 = 100%)
        self.manual_group.set_manual_dimmer(1.0)

        # Fixtures should now have dimmer_value = 255
        assert self.manual_fixture_1.dimmer_value == 255
        assert self.manual_fixture_2.dimmer_value == 255
        assert self.manual_fixture_1.values[0] == 255
        assert self.manual_fixture_2.values[0] == 255

        # Set manual dimmer to half (0.5 = 50%)
        self.manual_group.set_manual_dimmer(0.5)

        # Fixtures should now have dimmer_value = 127.5
        assert self.manual_fixture_1.dimmer_value == 127.5
        assert self.manual_fixture_2.dimmer_value == 127.5
        assert self.manual_fixture_1.values[0] == 127
        assert self.manual_fixture_2.values[0] == 127

        # Set manual dimmer to off (0.0 = 0%)
        self.manual_group.set_manual_dimmer(0.0)

        # Fixtures should now have dimmer_value = 0
        assert self.manual_fixture_1.dimmer_value == 0
        assert self.manual_fixture_2.dimmer_value == 0
        assert self.manual_fixture_1.values[0] == 0
        assert self.manual_fixture_2.values[0] == 0

    def test_renderer_get_dimmer_converts_to_0_1_range(self):
        """Test that renderer correctly converts fixture dimmer (0-255) to 0-1 range"""
        # Create a mock room renderer
        room_renderer = Mock()

        # Create renderer for manual fixture
        renderer = BulbRenderer(self.manual_fixture_1, room_renderer)

        # Set fixture dimmer to 255
        self.manual_fixture_1.set_dimmer(255)

        # Renderer should return 1.0 (255/255)
        assert renderer.get_dimmer() == 1.0

        # Set fixture dimmer to 127.5
        self.manual_fixture_1.set_dimmer(127.5)

        # Renderer should return 0.5 (127.5/255)
        assert renderer.get_dimmer() == 0.5

        # Set fixture dimmer to 0
        self.manual_fixture_1.set_dimmer(0)

        # Renderer should return 0.0 (0/255)
        assert renderer.get_dimmer() == 0.0

    def test_renderer_shows_beam_when_dimmer_above_threshold(self):
        """Test that renderer's render_transparent is called and would show beam when dimmer > 0.05"""
        # Create a mock room renderer with necessary methods
        room_renderer = Mock()
        room_renderer.local_position = MagicMock()
        room_renderer.local_rotation = MagicMock()
        room_renderer.render_cone_beam = Mock()
        room_renderer.convert_2d_to_3d = Mock(return_value=(0.0, 0.0, 3.0))

        # Setup context managers
        room_renderer.local_position.return_value.__enter__ = Mock()
        room_renderer.local_position.return_value.__exit__ = Mock()
        room_renderer.local_rotation.return_value.__enter__ = Mock()
        room_renderer.local_rotation.return_value.__exit__ = Mock()

        # Create renderer for manual fixture
        renderer = BulbRenderer(self.manual_fixture_1, room_renderer)

        # Create a frame with time 0
        frame = Frame({FrameSignal.sustained_low: 0.0})

        # Test 1: Dimmer = 0 (no beam)
        self.manual_fixture_1.set_dimmer(0)
        renderer.render_transparent(None, (1200.0, 1200.0), frame)
        room_renderer.render_cone_beam.assert_not_called()

        # Reset mock
        room_renderer.render_cone_beam.reset_mock()

        # Test 2: Dimmer = 0.03 * 255 = 7.65 (below threshold of 0.05, no beam)
        self.manual_fixture_1.set_dimmer(7.65)
        renderer.render_transparent(None, (1200.0, 1200.0), frame)
        room_renderer.render_cone_beam.assert_not_called()

        # Reset mock
        room_renderer.render_cone_beam.reset_mock()

        # Test 3: Dimmer = 0.1 * 255 = 25.5 (above threshold, beam should render)
        self.manual_fixture_1.set_dimmer(25.5)
        renderer.render_transparent(None, (1200.0, 1200.0), frame)
        room_renderer.render_cone_beam.assert_called_once()

        # Reset mock
        room_renderer.render_cone_beam.reset_mock()

        # Test 4: Dimmer = 255 (full brightness, beam should render)
        self.manual_fixture_1.set_dimmer(255)
        renderer.render_transparent(None, (1200.0, 1200.0), frame)
        room_renderer.render_cone_beam.assert_called_once()

    def test_full_integration_keyboard_to_renderer(self):
        """Test full integration: keyboard press -> state -> manual group -> fixture -> renderer"""
        # Create a mock room renderer with necessary methods
        room_renderer = Mock()
        room_renderer.local_position = MagicMock()
        room_renderer.local_rotation = MagicMock()
        room_renderer.render_cone_beam = Mock()
        room_renderer.convert_2d_to_3d = Mock(return_value=(0.0, 0.0, 3.0))

        # Setup context managers
        room_renderer.local_position.return_value.__enter__ = Mock()
        room_renderer.local_position.return_value.__exit__ = Mock()
        room_renderer.local_rotation.return_value.__enter__ = Mock()
        room_renderer.local_rotation.return_value.__exit__ = Mock()

        # Create renderer for manual fixture
        renderer = BulbRenderer(self.manual_fixture_1, room_renderer)

        # Create a frame
        frame = Frame({FrameSignal.sustained_low: 0.0})

        # Step 1: Initially, dimmer is 0, no beam
        renderer.render_transparent(None, (1200.0, 1200.0), frame)
        room_renderer.render_cone_beam.assert_not_called()

        # Step 2: Press M key (starts fading lights on)
        self.handler.on_key_press(pyglet.window.key.M, 0)

        # Step 3: Simulate 0.5s passing to reach full brightness
        self.handler.update_manual_dimmer(0.5)

        # Step 4: Apply state to manual group (simulating what director.render() does)
        self.manual_group.set_manual_dimmer(self.state.manual_dimmer)

        # Step 6: Verify fixture dimmer is now 255
        assert self.manual_fixture_1.get_dimmer() == 255

        # Step 7: Verify renderer sees dimmer as 1.0
        assert renderer.get_dimmer() == 1.0

        # Step 8: Verify renderer now shows beam
        room_renderer.render_cone_beam.reset_mock()
        renderer.render_transparent(None, (1200.0, 1200.0), frame)
        room_renderer.render_cone_beam.assert_called_once()

        # Step 9: Press K key (starts fading lights off)
        self.handler.on_key_press(pyglet.window.key.K, 0)

        # Step 10: Simulate 0.5s passing to reach off
        self.handler.update_manual_dimmer(0.5)

        # Step 11: Apply state to manual group again
        self.manual_group.set_manual_dimmer(self.state.manual_dimmer)

        # Step 13: Verify fixture dimmer is now 0
        assert self.manual_fixture_1.dimmer_value == 0
        assert self.manual_fixture_1.get_dimmer() == 0

        # Step 14: Verify renderer sees dimmer as 0.0
        assert renderer.get_dimmer() == 0.0

        # Step 15: Verify renderer no longer shows beam
        room_renderer.render_cone_beam.reset_mock()
        renderer.render_transparent(None, (1200.0, 1200.0), frame)
        room_renderer.render_cone_beam.assert_not_called()

    def test_manual_group_get_dimmer_returns_255_range(self):
        """Test that ManualGroup.get_dimmer() returns value in 0-255 range for consistency"""
        # Set manual dimmer to 1.0 (100%)
        self.manual_group.set_manual_dimmer(1.0)
        assert self.manual_group.get_dimmer() == 255

        # Set manual dimmer to 0.5 (50%)
        self.manual_group.set_manual_dimmer(0.5)
        assert self.manual_group.get_dimmer() == 127.5

        # Set manual dimmer to 0.0 (0%)
        self.manual_group.set_manual_dimmer(0.0)
        assert self.manual_group.get_dimmer() == 0

    def test_beam_alpha_matches_dimmer_value(self):
        """Test that beam alpha value matches expected dimmer for full brightness"""
        # Create a mock room renderer
        room_renderer = Mock()
        room_renderer.local_position = MagicMock()
        room_renderer.local_rotation = MagicMock()
        room_renderer.render_cone_beam = Mock()
        room_renderer.convert_2d_to_3d = Mock(return_value=(0.0, 0.0, 3.0))

        # Setup context managers
        room_renderer.local_position.return_value.__enter__ = Mock()
        room_renderer.local_position.return_value.__exit__ = Mock()
        room_renderer.local_rotation.return_value.__enter__ = Mock()
        room_renderer.local_rotation.return_value.__exit__ = Mock()

        # Create renderer for manual fixture
        renderer = BulbRenderer(self.manual_fixture_1, room_renderer)
        frame = Frame({FrameSignal.sustained_low: 0.0})

        # Set fixture to full brightness (255)
        self.manual_fixture_1.set_dimmer(255)

        # Verify renderer sees correct dimmer value
        assert renderer.get_dimmer() == 1.0
        assert renderer.get_effective_dimmer(frame) == 1.0

        # Render transparent (beam)
        renderer.render_transparent(None, (1200.0, 1200.0), frame)

        # Check that render_cone_beam was called with correct alpha
        room_renderer.render_cone_beam.assert_called_once()
        call_args = room_renderer.render_cone_beam.call_args
        # Alpha should be dimmer * 0.4 = 1.0 * 0.4 = 0.4
        assert call_args[1]["alpha"] == 0.4
