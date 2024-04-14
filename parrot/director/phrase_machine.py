import numpy as np
from parrot.director.frame import Frame, FrameSignal
from parrot.state import State


THROTTLE_SECONDS = 8
HYPE_DECAY = 0.01
HYPE_TRIGGER_DELTA = 0.3


class PhraseMachine:
    def __init__(self, state: State):
        self.state = state
        self.sustained_high_trough_time = None
        self.sustained_high_peak_time = None
        self.signals = {FrameSignal.hype: 0}
        self.last_hype = 0

    def deploy_hype(self, frame: Frame):
        self.signals[FrameSignal.hype] = 1
        self.last_hype = frame.time
        # print hype deployed with emojis
        print("Hype deployed! 🚀")

    def step(self, frame: Frame):

        self.signals[FrameSignal.hype] *= 1 - HYPE_DECAY

        min = np.min(frame.timeseries[FrameSignal.sustained_high.name][-200:])
        delta = frame[FrameSignal.sustained_high] - min

        if (
            delta > HYPE_TRIGGER_DELTA
            and frame.time - self.last_hype > THROTTLE_SECONDS
        ):
            self.deploy_hype(frame)

        # if frame[FrameSignal.sustained_high] < TROUGH_LEVEL and (
        #     self.sustained_high_peak_time is None
        #     or frame.time - self.sustained_high_peak_time > THROTTLE_SECONDS
        # ):
        #     if self.sustained_high_trough_time is None:
        #         print("Trough detected")
        #     self.sustained_high_trough_time = frame.time
        #     self.sustained_high_peak_time = None

        # if (
        #     frame[FrameSignal.sustained_high] > PEAK_LEVEL
        #     and self.sustained_high_trough_time is not None
        #     and frame.time - self.sustained_high_trough_time
        #     <= TROUGH_TO_PEAK_MAX_SECONDS
        # ):
        #     self.sustained_high_trough_time = None
        #     self.sustained_high_peak_time = frame.time
        #     print("Peak detected")
        #     self.signals[FrameSignal.hype] = 1

        return self.signals
