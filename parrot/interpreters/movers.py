import math
from parrot.interpreters.base import InterpreterBase
from parrot.patch.chauvet import ChauvetSpot160


class MoverBeat(InterpreterBase[ChauvetSpot160]):
    def __init__(self, subject: ChauvetSpot160):
        super().__init__(subject)
        self.signal = "drums"

    def step(self, frame, scheme):
        self.subject.set_dimmer(frame[self.signal] * 255)
        self.subject.set_color(scheme.fg)
        self.subject.set_pan(math.cos(frame.time) * 127 + 128)
        self.subject.set_tilt(math.sin(frame.time) * 127 + 128)
