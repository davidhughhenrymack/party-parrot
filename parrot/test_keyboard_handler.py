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

    def test_mode_switch_chill(self):
        """Test that F key switches to chill mode"""
        result = self.handler.on_key_release(pyglet.window.key.F, 0)
        assert result is True
        self.state.set_mode.assert_called_once_with(Mode.chill)

    def test_mode_switch_rave(self):
        """Test that C key switches to rave mode"""
        result = self.handler.on_key_release(pyglet.window.key.C, 0)
        assert result is True
        self.state.set_mode.assert_called_once_with(Mode.rave)

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
