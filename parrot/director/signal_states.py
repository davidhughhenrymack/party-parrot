from parrot.director.frame import FrameSignal
from typing import Dict


class SignalStates:
    def __init__(self):
        self.states: Dict[FrameSignal, float] = {
            FrameSignal.strobe: 0.0,
            FrameSignal.big_pulse: 0.0,
            FrameSignal.small_pulse: 0.0,
            FrameSignal.twinkle: 0.0,
        }

    def set_signal(self, signal: FrameSignal, value: float):
        """Set a signal state value."""
        self.states[signal] = value

    def get_states(self) -> Dict[FrameSignal, float]:
        """Get all signal states."""
        return self.states.copy()
