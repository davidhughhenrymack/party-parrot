"""Tests for the KeyboardHandler class"""

import pytest
from unittest.mock import Mock, MagicMock
import pyglet

from parrot.keyboard_handler import KeyboardHandler
from parrot.director.director import Director
from parrot.director.mode import Mode
from parrot.director.frame import FrameSignal
from parrot.director.signal_states import SignalStates
from parrot.state import State
from parrot.utils.overlay_ui import OverlayUI
from parrot.vj.vj_mode import VJMode


class TestKeyboardHandler:
    """Tests for keyboard input handling"""

    def setup_method(self):
        """Setup test fixtures"""
        # Use spec to make mocks compatible with beartype
        self.director = Mock(spec=Director)
        self.overlay = Mock(spec=OverlayUI)
        self.signal_states = Mock(spec=SignalStates)
        self.state = Mock(spec=State)
        self.handler = KeyboardHandler(
            self.director, self.overlay, self.signal_states, self.state
        )

    def test_space_regenerates_all(self):
        """Test that SPACE key regenerates both lighting and VJ"""
        result = self.handler.on_key_press(pyglet.window.key.SPACE, 0)
        assert result is True
        self.director.generate_all.assert_called_once()

    def test_enter_toggles_overlay(self):
        """Test that ENTER key toggles overlay"""
        result = self.handler.on_key_press(pyglet.window.key.ENTER, 0)
        assert result is True
        self.overlay.toggle.assert_called_once()

    def test_return_toggles_overlay(self):
        """Test that RETURN key also toggles overlay"""
        result = self.handler.on_key_press(pyglet.window.key.RETURN, 0)
        assert result is True
        self.overlay.toggle.assert_called_once()

    def test_signal_button_press_i(self):
        """Test that I key sets small_blinder signal on press"""
        result = self.handler.on_key_press(pyglet.window.key.I, 0)
        assert result is True
        self.signal_states.set_signal.assert_called_once_with(
            FrameSignal.small_blinder, 1.0
        )

    def test_signal_button_release_i(self):
        """Test that I key clears small_blinder signal on release"""
        result = self.handler.on_key_release(pyglet.window.key.I, 0)
        assert result is True
        self.signal_states.set_signal.assert_called_once_with(
            FrameSignal.small_blinder, 0.0
        )

    def test_mode_navigate_up(self):
        """Test that C key navigates up lighting modes (towards rave)"""
        # Start at chill
        self.state.mode = Mode.chill

        result = self.handler.on_key_release(pyglet.window.key.C, 0)
        assert result is True
        self.state.set_mode.assert_called_once_with(Mode.rave)

    def test_mode_navigate_down(self):
        """Test that D key navigates down lighting modes (towards blackout)"""
        # Start at chill
        self.state.mode = Mode.chill

        result = self.handler.on_key_release(pyglet.window.key.D, 0)
        assert result is True
        self.state.set_mode.assert_called_once_with(Mode.blackout)

    def test_mode_navigate_up_arrow(self):
        """Test that UP arrow key navigates up lighting modes (towards rave)"""
        # Start at chill
        self.state.mode = Mode.chill

        result = self.handler.on_key_press(pyglet.window.key.UP, 0)
        assert result is True
        self.state.set_mode.assert_called_once_with(Mode.rave)

    def test_mode_navigate_down_arrow(self):
        """Test that DOWN arrow key navigates down lighting modes (towards blackout)"""
        # Start at chill
        self.state.mode = Mode.chill

        result = self.handler.on_key_press(pyglet.window.key.DOWN, 0)
        assert result is True
        self.state.set_mode.assert_called_once_with(Mode.blackout)

    def test_mode_no_wrap_at_highest(self):
        """Test that C doesn't wrap at highest lighting mode (rave)"""
        # Start at rave
        self.state.mode = Mode.rave

        result = self.handler.on_key_release(pyglet.window.key.C, 0)
        assert result is True
        # Should not call set_mode since we're at the top
        self.state.set_mode.assert_not_called()

    def test_mode_no_wrap_at_lowest(self):
        """Test that D doesn't wrap at lowest lighting mode (blackout)"""
        # Start at blackout
        self.state.mode = Mode.blackout

        result = self.handler.on_key_release(pyglet.window.key.D, 0)
        assert result is True
        # Should not call set_mode since we're at the bottom
        self.state.set_mode.assert_not_called()

    def test_mode_up_arrow_no_wrap_at_highest(self):
        """Test that UP arrow doesn't wrap at highest lighting mode (rave)"""
        # Start at rave
        self.state.mode = Mode.rave

        result = self.handler.on_key_press(pyglet.window.key.UP, 0)
        assert result is True
        # Should not call set_mode since we're at the top
        self.state.set_mode.assert_not_called()

    def test_mode_down_arrow_no_wrap_at_lowest(self):
        """Test that DOWN arrow doesn't wrap at lowest lighting mode (blackout)"""
        # Start at blackout
        self.state.mode = Mode.blackout

        result = self.handler.on_key_press(pyglet.window.key.DOWN, 0)
        assert result is True
        # Should not call set_mode since we're at the bottom
        self.state.set_mode.assert_not_called()

    def test_s_key_shifts_lighting_only(self):
        """Test that S key triggers lighting-only shift"""
        result = self.handler.on_key_release(pyglet.window.key.S, 0)
        assert result is True
        self.director.shift_lighting_only.assert_called_once()

    def test_o_key_shifts_vj_only(self):
        """Test that O key triggers VJ-only shift"""
        result = self.handler.on_key_release(pyglet.window.key.O, 0)
        assert result is True
        self.director.shift_vj_only.assert_called_once()

    def test_unhandled_key_returns_false(self):
        """Test that unhandled keys return False"""
        result = self.handler.on_key_press(pyglet.window.key.Z, 0)
        assert result is False
        result = self.handler.on_key_release(pyglet.window.key.Z, 0)
        assert result is False

    def test_vj_mode_navigate_right(self):
        """Test that RIGHT arrow key navigates to next VJ mode"""
        # Start at golden_age
        self.state.vj_mode = VJMode.golden_age

        result = self.handler.on_key_press(pyglet.window.key.RIGHT, 0)
        assert result is True
        self.state.set_vj_mode.assert_called_once_with(VJMode.music_vids)

    def test_vj_mode_navigate_left(self):
        """Test that LEFT arrow key navigates to previous VJ mode"""
        # Start at music_vids
        self.state.vj_mode = VJMode.music_vids

        result = self.handler.on_key_press(pyglet.window.key.LEFT, 0)
        assert result is True
        self.state.set_vj_mode.assert_called_once_with(VJMode.golden_age)

    def test_vj_mode_no_wrap_at_last(self):
        """Test that RIGHT arrow doesn't wrap at last VJ mode"""
        # Start at last mode
        self.state.vj_mode = VJMode.full_rave

        result = self.handler.on_key_press(pyglet.window.key.RIGHT, 0)
        assert result is True
        # Should not call set_vj_mode since we're at the end
        self.state.set_vj_mode.assert_not_called()

    def test_vj_mode_no_wrap_at_first(self):
        """Test that LEFT arrow doesn't wrap at first VJ mode"""
        # Start at first mode
        self.state.vj_mode = VJMode.blackout

        result = self.handler.on_key_press(pyglet.window.key.LEFT, 0)
        assert result is True
        # Should not call set_vj_mode since we're at the beginning
        self.state.set_vj_mode.assert_not_called()

    def test_vj_mode_navigate_includes_hiphop(self):
        """Test that navigation includes the new hiphop mode"""
        # Start at music_vids
        self.state.vj_mode = VJMode.music_vids

        # Navigate right to hiphop
        result = self.handler.on_key_press(pyglet.window.key.RIGHT, 0)
        assert result is True
        self.state.set_vj_mode.assert_called_once_with(VJMode.hiphop)

        # Reset mock
        self.state.set_vj_mode.reset_mock()

        # Navigate left from early_rave back to hiphop
        self.state.vj_mode = VJMode.early_rave
        result = self.handler.on_key_press(pyglet.window.key.LEFT, 0)
        assert result is True
        self.state.set_vj_mode.assert_called_once_with(VJMode.hiphop)

    def test_vj_mode_navigate_with_f_key(self):
        """Test that F key navigates up VJ modes (towards full_rave)"""
        # Start at hiphop
        self.state.vj_mode = VJMode.hiphop

        result = self.handler.on_key_release(pyglet.window.key.F, 0)
        assert result is True
        self.state.set_vj_mode.assert_called_once_with(VJMode.early_rave)

    def test_vj_mode_navigate_with_e_key(self):
        """Test that E key navigates down VJ modes (towards blackout)"""
        # Start at early_rave
        self.state.vj_mode = VJMode.early_rave

        result = self.handler.on_key_release(pyglet.window.key.E, 0)
        assert result is True
        self.state.set_vj_mode.assert_called_once_with(VJMode.hiphop)

    def test_manual_dimmer_m_key_press_starts_fade_up(self):
        """Test that M key starts fading up"""
        result = self.handler.on_key_press(pyglet.window.key.M, 0)
        assert result is True
        assert self.handler.manual_fade_direction == 1

    def test_manual_dimmer_k_key_press_starts_fade_down(self):
        """Test that K key starts fading down"""
        result = self.handler.on_key_press(pyglet.window.key.K, 0)
        assert result is True
        assert self.handler.manual_fade_direction == -1

    def test_manual_dimmer_release_stops_fade(self):
        """Test that releasing M or K stops the fade"""
        # Start fade up
        self.handler.on_key_press(pyglet.window.key.M, 0)
        assert self.handler.manual_fade_direction == 1

        # Release M
        result = self.handler.on_key_release(pyglet.window.key.M, 0)
        assert result is True
        assert self.handler.manual_fade_direction == 0

        # Start fade down
        self.handler.on_key_press(pyglet.window.key.K, 0)
        assert self.handler.manual_fade_direction == -1

        # Release K
        result = self.handler.on_key_release(pyglet.window.key.K, 0)
        assert result is True
        assert self.handler.manual_fade_direction == 0

    def test_manual_dimmer_update_fades_up(self):
        """Test that update_manual_dimmer progressively fades up when M is held"""
        # Set initial dimmer to 0
        self.state.manual_dimmer = 0.0

        # Press M to start fade up
        self.handler.on_key_press(pyglet.window.key.M, 0)

        # Simulate 0.25 seconds passing (should reach 0.5 at speed 2.0)
        self.handler.update_manual_dimmer(0.25)
        self.state.set_manual_dimmer.assert_called_with(0.5)

        # Update state
        self.state.manual_dimmer = 0.5

        # Simulate another 0.25 seconds (should reach 1.0)
        self.handler.update_manual_dimmer(0.25)
        self.state.set_manual_dimmer.assert_called_with(1.0)

        # Update state
        self.state.manual_dimmer = 1.0

        # Simulate more time (should clamp at 1.0)
        self.handler.update_manual_dimmer(0.25)
        self.state.set_manual_dimmer.assert_called_with(1.0)

    def test_manual_dimmer_update_fades_down(self):
        """Test that update_manual_dimmer progressively fades down when K is held"""
        # Set initial dimmer to 1.0
        self.state.manual_dimmer = 1.0

        # Press K to start fade down
        self.handler.on_key_press(pyglet.window.key.K, 0)

        # Simulate 0.25 seconds passing (should reach 0.5 at speed 2.0)
        self.handler.update_manual_dimmer(0.25)
        self.state.set_manual_dimmer.assert_called_with(0.5)

        # Update state
        self.state.manual_dimmer = 0.5

        # Simulate another 0.25 seconds (should reach 0.0)
        self.handler.update_manual_dimmer(0.25)
        self.state.set_manual_dimmer.assert_called_with(0.0)

        # Update state
        self.state.manual_dimmer = 0.0

        # Simulate more time (should clamp at 0.0)
        self.handler.update_manual_dimmer(0.25)
        self.state.set_manual_dimmer.assert_called_with(0.0)

    def test_manual_dimmer_update_does_nothing_when_not_fading(self):
        """Test that update_manual_dimmer does nothing when no key is held"""
        self.state.manual_dimmer = 0.5

        # No key pressed, so manual_fade_direction should be 0
        assert self.handler.manual_fade_direction == 0

        # Simulate time passing
        self.handler.update_manual_dimmer(0.1)

        # set_manual_dimmer should not be called
        self.state.set_manual_dimmer.assert_not_called()

    def test_blackout_toggle_enters_blackout(self):
        """Test that B key enters blackout mode and saves current modes"""
        # Set current modes
        self.state.mode = Mode.rave
        self.state.vj_mode = VJMode.full_rave

        # Press B to enter blackout
        result = self.handler.on_key_press(pyglet.window.key.B, 0)
        assert result is True

        # Check that modes were saved and blackout was set
        assert self.handler.previous_mode == Mode.rave
        assert self.handler.previous_vj_mode == VJMode.full_rave
        assert self.handler.blackout_active is True
        self.state.set_mode.assert_called_once_with(Mode.blackout)
        self.state.set_vj_mode.assert_called_once_with(VJMode.blackout)

    def test_blackout_toggle_exits_blackout(self):
        """Test that B key exits blackout and restores previous modes"""
        # Set up: already in blackout with saved modes
        self.handler.blackout_active = True
        self.handler.previous_mode = Mode.chill
        self.handler.previous_vj_mode = VJMode.early_rave
        self.state.mode = Mode.blackout
        self.state.vj_mode = VJMode.blackout

        # Press B to exit blackout
        result = self.handler.on_key_press(pyglet.window.key.B, 0)
        assert result is True

        # Check that modes were restored
        assert self.handler.blackout_active is False
        self.state.set_mode.assert_called_once_with(Mode.chill)
        self.state.set_vj_mode.assert_called_once_with(VJMode.early_rave)

    def test_blackout_toggle_full_cycle(self):
        """Test a full blackout toggle cycle: enter then exit"""
        # Start in rave mode
        self.state.mode = Mode.rave
        self.state.vj_mode = VJMode.music_vids

        # First press: enter blackout
        self.handler.on_key_press(pyglet.window.key.B, 0)
        assert self.handler.blackout_active is True
        assert self.handler.previous_mode == Mode.rave
        assert self.handler.previous_vj_mode == VJMode.music_vids

        # Update mock state to reflect blackout
        self.state.mode = Mode.blackout
        self.state.vj_mode = VJMode.blackout
        self.state.set_mode.reset_mock()
        self.state.set_vj_mode.reset_mock()

        # Second press: exit blackout
        self.handler.on_key_press(pyglet.window.key.B, 0)
        assert self.handler.blackout_active is False
        self.state.set_mode.assert_called_once_with(Mode.rave)
        self.state.set_vj_mode.assert_called_once_with(VJMode.music_vids)
