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
        # blackout (lowest) -> chill -> rave_gentle -> rave (highest)
        self.modes = [Mode.blackout, Mode.chill, Mode.rave_gentle, Mode.rave]

        # Track manual dimmer fade state
        self.manual_fade_direction = 0  # 0=none, 1=up (M), -1=down (K)
        self.manual_fade_speed = 2.0  # Full fade in 0.5 seconds (2.0 per second)

        # Track blackout toggle state
        self.blackout_active = False
        self.previous_mode = None
        self.previous_vj_mode = None

    def on_key_press(self, symbol: int, modifiers: int) -> bool:
        """Handle key press events"""
        # VJ mode navigation
        if symbol == pyglet.window.key.LEFT:
            self._navigate_vj_mode_previous()
            return True
        elif symbol == pyglet.window.key.RIGHT:
            self._navigate_vj_mode_next()
            return True

        # Lighting mode navigation (UP = towards rave, DOWN = towards blackout)
        elif symbol == pyglet.window.key.UP:
            self._navigate_mode_up()
            return True
        elif symbol == pyglet.window.key.DOWN:
            self._navigate_mode_down()
            return True

        # Keep current functionality
        elif symbol == pyglet.window.key.SPACE:
            self.director.generate_all()
            return True  # Event handled
        elif symbol == pyglet.window.key.BACKSLASH:
            if self.show_fixture_mode_callback:
                self.show_fixture_mode_callback()
            return True  # Event handled

        # Signal buttons (press and hold)
        elif symbol == pyglet.window.key.I or symbol == pyglet.window.key._1:
            self.signal_states.set_signal(FrameSignal.small_blinder, 1.0)
            return True
        elif symbol == pyglet.window.key.G or symbol == pyglet.window.key._2:
            self.signal_states.set_signal(FrameSignal.big_blinder, 1.0)
            return True
        elif symbol == pyglet.window.key.H or symbol == pyglet.window.key._3:
            self.signal_states.set_signal(FrameSignal.strobe, 1.0)
            return True
        elif symbol == pyglet.window.key.J or symbol == pyglet.window.key._4:
            self.signal_states.set_signal(FrameSignal.pulse, 1.0)
            return True

        # Manual dimmer controls (press and hold to fade up/down)
        elif symbol == pyglet.window.key.M:
            self.manual_fade_direction = 1  # Fade up
            return True
        elif symbol == pyglet.window.key.K:
            self.manual_fade_direction = -1  # Fade down
            return True

        # Blackout toggle
        elif symbol == pyglet.window.key.B:
            self._toggle_blackout()
            return True

        return False

    def on_key_release(self, symbol: int, modifiers: int) -> bool:
        """Handle key release events"""
        # Signal buttons (release)
        if symbol == pyglet.window.key.I or symbol == pyglet.window.key._1:
            self.signal_states.set_signal(FrameSignal.small_blinder, 0.0)
            return True
        elif symbol == pyglet.window.key.G or symbol == pyglet.window.key._2:
            self.signal_states.set_signal(FrameSignal.big_blinder, 0.0)
            return True
        elif symbol == pyglet.window.key.H or symbol == pyglet.window.key._3:
            self.signal_states.set_signal(FrameSignal.strobe, 0.0)
            return True
        elif symbol == pyglet.window.key.J or symbol == pyglet.window.key._4:
            self.signal_states.set_signal(FrameSignal.pulse, 0.0)
            return True

        # Manual dimmer controls - stop fading when key released
        if symbol == pyglet.window.key.M or symbol == pyglet.window.key.K:
            self.manual_fade_direction = 0
            # Return False so other handlers can run if needed
            # (but we handled the M/K press, so the fade has stopped)
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
        elif symbol == pyglet.window.key.N:
            self.director.shift_lighting_only()
            return True
        elif symbol == pyglet.window.key.S:
            self.director.shift_color_scheme()
            return True
        elif symbol == pyglet.window.key.O:
            self.director.shift_vj_only()
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

    def update_manual_dimmer(self, dt: float):
        """Update manual dimmer fade - call this each frame with delta time

        Args:
            dt: Delta time in seconds since last update
        """
        if self.manual_fade_direction != 0:
            # Calculate new dimmer value
            current = self.state.manual_dimmer
            delta = self.manual_fade_direction * self.manual_fade_speed * dt
            new_value = current + delta

            # Clamp to 0-1 range
            new_value = max(0.0, min(1.0, new_value))

            # Update state
            self.state.set_manual_dimmer(new_value)

    def _toggle_blackout(self):
        """Toggle blackout mode - remember and restore previous modes"""
        if not self.blackout_active:
            # Entering blackout: remember current modes
            self.previous_mode = self.state.mode
            self.previous_vj_mode = self.state.vj_mode

            # Set both to blackout
            self.state.set_mode(Mode.blackout)
            self.state.set_vj_mode(VJMode.blackout)

            self.blackout_active = True
        else:
            # Exiting blackout: restore previous modes
            if self.previous_mode is not None:
                self.state.set_mode(self.previous_mode)
            if self.previous_vj_mode is not None:
                self.state.set_vj_mode(self.previous_vj_mode)

            self.blackout_active = False
