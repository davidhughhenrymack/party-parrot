from parrot.interpreters.base import InterpreterBase
from parrot.fixtures.base import FixtureBase


class DimmerBinaryLatched(InterpreterBase[FixtureBase]):
    def __init__(self, subject: FixtureBase, signal="sustained"):
        super().__init__(subject)
        self.signal = signal
        self.switch = False

    def step(self, frame, scheme):
        if frame["sustained"] > 0.6:
            self.switch = True
        elif frame["sustained"] < 0.4:
            self.switch = False

        if self.switch:
            self.subject.set_dimmer(255)
        else:
            self.subject.set_dimmer(0)
