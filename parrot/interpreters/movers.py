import math
from parrot.interpreters.base import InterpreterBase
from parrot.fixtures import FixtureBase


class MoverCircleAndColor(InterpreterBase[FixtureBase]):
    def __init__(self, subject: FixtureBase):
        super().__init__(subject)

    def step(self, frame, scheme):
        self.subject.set_color(scheme.fg)
        self.subject.set_pan(math.cos(frame.time) * 127 + 128)
        self.subject.set_tilt(math.sin(frame.time) * 127 + 128)


class MoverBeat(InterpreterBase[FixtureBase]):
    def __init__(self, subject: FixtureBase):
        super().__init__(subject)
        self.signal = "drums"
        self.movement = MoverCircleAndColor(subject)

    def step(self, frame, scheme):
        self.movement.step(frame, scheme)

        if frame["sustained"] > 0.7:
            self.subject.set_dimmer(100)
            self.subject.set_strobe(200)
        elif frame[self.signal] > 0.4:
            self.subject.set_dimmer(frame[self.signal] * 255)
            self.subject.set_strobe(0)
        else:
            self.subject.set_dimmer(0)
            self.subject.set_strobe(0)
