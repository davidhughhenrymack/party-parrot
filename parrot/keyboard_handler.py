"""Keyboard handler for Party Parrot GL window"""

import pyglet
from beartype import beartype

from parrot.director.director import Director
from parrot.director.mode import Mode
from parrot.director.frame import FrameSignal
from parrot.director.signal_states import SignalStates
from parrot.state import State
from parrot.utils.overlay_ui import OverlayUI
from parrot.vj.vj_mode import VJMode


# Note: @beartype removed to allow mocking in tests
class KeyboardHandler:
    """Handles keyboard input for the GL window application"""

    def __init__(
        self,
        director: Director,
        overlay: OverlayUI,
        signal_states: SignalStates,
        state: State,
        show_fixture_mode_callback=None,
    ):
        self.director = director
        self.overlay = overlay
        self.signal_states = signal_states
        self.state = state
        self.show_fixture_mode_callback = show_fixture_mode_callback

        # Get list of VJ modes in enum order (blackout is lowest/first)
        self.vj_modes = list(VJMode)

        # Get list of lighting modes ordered from lowest to highest intensity
        # blackout (lowest) -> chill -> rave (highest)
        self.modes = [Mode.blackout, Mode.chill, Mode.rave]

    def on_key_press(self, symbol: int, modifiers: int) -> bool:
        """Handle key press events"""
        # VJ mode navigation
        if symbol == pyglet.window.key.LEFT:
            self._navigate_vj_mode_previous()
            return True
        elif symbol == pyglet.window.key.RIGHT:
            self._navigate_vj_mode_next()
            return True

        # Keep current functionality
        elif symbol == pyglet.window.key.SPACE:
            self.director.generate_interpreters()
            return True  # Event handled
        elif symbol == pyglet.window.key.RETURN or symbol == pyglet.window.key.ENTER:
            self.overlay.toggle()
            return True  # Event handled
        elif symbol == pyglet.window.key.BACKSLASH:
            if self.show_fixture_mode_callback:
                self.show_fixture_mode_callback()
            return True  # Event handled

        # Signal buttons (press and hold)
        elif symbol == pyglet.window.key.I:
            self.signal_states.set_signal(FrameSignal.small_blinder, 1.0)
            return True
        elif symbol == pyglet.window.key.G:
            self.signal_states.set_signal(FrameSignal.big_blinder, 1.0)
            return True
        elif symbol == pyglet.window.key.H:
            self.signal_states.set_signal(FrameSignal.strobe, 1.0)
            return True
        elif symbol == pyglet.window.key.J:
            self.signal_states.set_signal(FrameSignal.pulse, 1.0)
            return True

        return False

    def on_key_release(self, symbol: int, modifiers: int) -> bool:
        """Handle key release events"""
        # Signal buttons (release)
        if symbol == pyglet.window.key.I:
            self.signal_states.set_signal(FrameSignal.small_blinder, 0.0)
            return True
        elif symbol == pyglet.window.key.G:
            self.signal_states.set_signal(FrameSignal.big_blinder, 0.0)
            return True
        elif symbol == pyglet.window.key.H:
            self.signal_states.set_signal(FrameSignal.strobe, 0.0)
            return True
        elif symbol == pyglet.window.key.J:
            self.signal_states.set_signal(FrameSignal.pulse, 0.0)
            return True

        # Lighting mode navigation (C = up towards rave, D = down towards blackout)
        elif symbol == pyglet.window.key.C:
            self._navigate_mode_up()
            return True
        elif symbol == pyglet.window.key.D:
            self._navigate_mode_down()
            return True

        # VJ mode navigation (E = down towards blackout, F = up towards full_rave)
        elif symbol == pyglet.window.key.E:
            self._navigate_vj_mode_previous()
            return True
        elif symbol == pyglet.window.key.F:
            self._navigate_vj_mode_next()
            return True

        # Director commands
        elif symbol == pyglet.window.key.S:
            self.director.generate_interpreters()
            return True
        elif symbol == pyglet.window.key.O:
            self.director.shift()
            return True

        return False

    def _navigate_vj_mode_next(self):
        """Navigate to the next VJ mode in enum order (no wrapping)"""
        current_mode = self.state.vj_mode
        current_index = self.vj_modes.index(current_mode)

        # Only move forward if we're not at the last mode
        if current_index < len(self.vj_modes) - 1:
            next_mode = self.vj_modes[current_index + 1]
            self.state.set_vj_mode(next_mode)

    def _navigate_vj_mode_previous(self):
        """Navigate to the previous VJ mode in enum order (no wrapping)"""
        current_mode = self.state.vj_mode
        current_index = self.vj_modes.index(current_mode)

        # Only move backward if we're not at the first mode
        if current_index > 0:
            prev_mode = self.vj_modes[current_index - 1]
            self.state.set_vj_mode(prev_mode)

    def _navigate_mode_up(self):
        """Navigate up lighting modes (towards rave, no wrapping)"""
        current_mode = self.state.mode
        current_index = self.modes.index(current_mode)

        # Only move up if we're not at the highest mode
        if current_index < len(self.modes) - 1:
            next_mode = self.modes[current_index + 1]
            self.state.set_mode(next_mode)

    def _navigate_mode_down(self):
        """Navigate down lighting modes (towards blackout, no wrapping)"""
        current_mode = self.state.mode
        current_index = self.modes.index(current_mode)

        # Only move down if we're not at the lowest mode
        if current_index > 0:
            prev_mode = self.modes[current_index - 1]
            self.state.set_mode(prev_mode)
