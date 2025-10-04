"""Keyboard handler for Party Parrot GL window"""

import pyglet
from beartype import beartype

from parrot.director.director import Director
from parrot.director.mode import Mode
from parrot.director.frame import FrameSignal
from parrot.director.signal_states import SignalStates
from parrot.state import State
from parrot.utils.overlay_ui import OverlayUI


@beartype
class KeyboardHandler:
    """Handles keyboard input for the GL window application"""

    def __init__(
        self,
        director: Director,
        overlay: OverlayUI,
        signal_states: SignalStates,
        state: State,
    ):
        self.director = director
        self.overlay = overlay
        self.signal_states = signal_states
        self.state = state

    def on_key_press(self, symbol: int, modifiers: int) -> bool:
        """Handle key press events"""
        # Keep current functionality
        if symbol == pyglet.window.key.SPACE:
            self.director.generate_interpreters()
            return True  # Event handled
        elif symbol == pyglet.window.key.RETURN or symbol == pyglet.window.key.ENTER:
            self.overlay.toggle()
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

        # Mode selection
        elif symbol == pyglet.window.key.E:
            print("⚡ Mode: Gentle")
            self.state.set_mode(Mode.gentle)
            return True
        elif symbol == pyglet.window.key.F:
            print("⚡ Mode: Chill")
            self.state.set_mode(Mode.chill)
            return True
        elif symbol == pyglet.window.key.C:
            print("⚡ Mode: Rave")
            self.state.set_mode(Mode.rave)
            return True
        elif symbol == pyglet.window.key.D:
            print("⚡ Mode: Blackout")
            self.state.set_mode(Mode.blackout)
            return True

        # Director commands
        elif symbol == pyglet.window.key.S:
            print("⚡ Regenerating interpreters...")
            self.director.generate_interpreters()
            return True
        elif symbol == pyglet.window.key.O:
            print("⚡ Shifting...")
            self.director.shift()
            return True

        return False
