from parrot.interpreters.base import InterpreterBase
from parrot.fixtures.base import FixtureBase
from parrot.utils.lerp import lerp


class DimmerBinaryLatched(InterpreterBase[FixtureBase]):
    def __init__(self, subject: FixtureBase, signal="sustained"):
        super().__init__(subject)
        self.signal = signal
        self.switch = False
        self.latch_until = 0

    def step(self, frame, scheme):
        if frame["sustained"] > 0.55:
            self.switch = True
            self.latch_until = frame.time + 0.5
        elif frame["sustained"] < 0.2:
            self.switch = False

        if self.switch or self.latch_until > frame.time:
            self.subject.set_dimmer(255)
        else:
            self.subject.set_dimmer(0)


class DimmerFadeLatched(InterpreterBase[FixtureBase]):
    def __init__(self, subject: FixtureBase, signal="sustained"):
        super().__init__(subject)
        self.signal = signal
        self.switch = False
        self.latch_until = 0
        self.memory = 0

    def step(self, frame, scheme):
        if frame[self.signal] > 0.55:
            self.switch = True
            self.latch_until = frame.time + 0.5
        elif frame[self.signal] < 0.2:
            self.switch = False

        if self.switch or self.latch_until > frame.time:
            self.memory = lerp(self.memory, 255, 0.1)
            self.subject.set_dimmer(self.memory)
        else:
            self.subject.set_dimmer(0)
