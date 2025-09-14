from parrot.director.frame import FrameSignal
from beartype import beartype


@beartype
class SignalStates:
    def __init__(self):
        self.states: dict[FrameSignal, float] = {
            FrameSignal.strobe: 0.0,
            FrameSignal.big_blinder: 0.0,
            FrameSignal.small_blinder: 0.0,
            FrameSignal.pulse: 0.0,
        }

    def set_signal(self, signal: FrameSignal, value: float):
        """Set a signal state value."""
        self.states[signal] = value

    def get_states(self) -> dict[FrameSignal, float]:
        """Get all signal states."""
        return self.states.copy()
