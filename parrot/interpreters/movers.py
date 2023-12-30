import math
from parrot.interpreters.base import InterpreterBase
from parrot.patch.chauvet import ChauvetSpot160


class MoverBeat(InterpreterBase[ChauvetSpot160]):
    def __init__(self, subject: ChauvetSpot160):
        super().__init__(subject)
        self.signal = "drums"

    def step(self, frame, scheme):
        self.subject.set_color(scheme.fg)

        if frame["sustained"] > 0.7:
            self.subject.set_dimmer(100)
            self.subject.set_strobe(200)
        elif frame[self.signal] > 0.2:
            self.subject.set_dimmer(frame[self.signal] * 255)
            self.subject.set_strobe(0)
        else:
            self.subject.set_dimmer(0)
            self.subject.set_strobe(0)

        self.subject.set_pan(math.cos(frame.time) * 127 + 128)
        self.subject.set_tilt(math.sin(frame.time) * 127 + 128)
