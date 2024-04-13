from parrot.interpreters.base import InterpreterBase
from parrot.director.frame import FrameSignal


class StrobeHighSustained(InterpreterBase):
    hype = 90

    def step(self, frame, scheme):
        for i in self.group:
            if frame[FrameSignal.sustained_low] > 0.4:
                i.set_strobe(255)
            else:
                i.set_dimmer(0)
