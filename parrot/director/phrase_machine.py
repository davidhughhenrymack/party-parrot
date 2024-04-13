from parrot.director.frame import FrameSignal
from parrot.state import State
from parrot.director.director import Director


TROUGH_TO_PEAK_MAX_SECONDS = 1
TROUGH_LEVEL = 0.1
PEAK_LEVEL = 0.35

THROTTLE_SECONDS = 8

HYPE_DECAY = 0.01


class PhraseMachine:
    def __init__(self, state: State):
        self.state = state
        self.sustained_low_trough_time = None
        self.sustained_low_peak_time = None
        self.signals = {FrameSignal.hype: 0}

    def step(self, frame, director: Director):

        self.signals[FrameSignal.hype] *= 1 - HYPE_DECAY

        if frame[FrameSignal.sustained_low] < TROUGH_LEVEL and (
            self.sustained_low_peak_time is None
            or frame.time - self.sustained_low_peak_time > THROTTLE_SECONDS
        ):
            if self.sustained_low_trough_time is None:
                print("Trough detected")
            self.sustained_low_trough_time = frame.time
            self.sustained_low_peak_time = None

        if (
            frame[FrameSignal.sustained_low] > PEAK_LEVEL
            and self.sustained_low_trough_time is not None
            and frame.time - self.sustained_low_trough_time
            <= TROUGH_TO_PEAK_MAX_SECONDS
        ):
            self.sustained_low_trough_time = None
            self.sustained_low_peak_time = frame.time
            print("Peak detected")
            self.signals[FrameSignal.hype] = 1
            director.shift()

        return self.signals
