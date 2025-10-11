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

    def test_space_regenerates_interpreters(self):
        """Test that SPACE key regenerates interpreters"""
        result = self.handler.on_key_press(pyglet.window.key.SPACE, 0)
        assert result is True
        self.director.generate_interpreters.assert_called_once()

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

    def test_director_shift(self):
        """Test that O key triggers director shift"""
        result = self.handler.on_key_release(pyglet.window.key.O, 0)
        assert result is True
        self.director.shift.assert_called_once()

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
