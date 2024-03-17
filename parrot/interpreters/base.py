from enum import Enum
import math
from typing import Generic, List, TypeVar
from parrot.director.frame import Frame
from parrot.fixtures.base import FixtureBase
from parrot.director.color_scheme import ColorScheme

Phrase = Enum("Phrase", ["intro_outro", "build", "drop", "breakdown"])

T = TypeVar("T", bound=FixtureBase)


class InterpreterBase(Generic[T]):
    def __init__(self, subject: T):
        self.subject = subject

    def step(self, frame: Frame, scheme: ColorScheme):
        pass


class GroupInterpreterBase(Generic[T]):
    def __init__(self, group: List[T]):
        self.group = group

    def step(self, frame: Frame, scheme: ColorScheme):
        pass


class Dimmer100(InterpreterBase):
    def __init__(self, subject: FixtureBase):
        super().__init__(subject)

    def step(self, frame, scheme):
        self.subject.set_dimmer(100)


class Dimmer30(InterpreterBase):
    def __init__(self, subject: FixtureBase):
        super().__init__(subject)

    def step(self, frame, scheme):
        self.subject.set_dimmer(30)


class ColorFg(InterpreterBase):
    def __init__(self, subject: FixtureBase):
        super().__init__(subject)

    def step(self, frame, scheme):
        self.subject.set_color(scheme.fg)


class MoveCircles(InterpreterBase):
    def __init__(self, subject: FixtureBase, multiplier=1):
        super().__init__(subject)
        self.multiplier = multiplier

    def step(self, frame, scheme):
        self.subject.set_pan(math.cos(frame.time * self.multiplier) * 127 + 128)
        self.subject.set_tilt(math.sin(frame.time * self.multiplier) * 127 + 128)


class FlashBeat(InterpreterBase[FixtureBase]):
    def __init__(self, subject: FixtureBase):
        super().__init__(subject)
        self.signal = "drums"

    def step(self, frame, scheme):
        if frame["sustained"] > 0.7:
            self.subject.set_dimmer(100)
            self.subject.set_strobe(200)
        elif frame[self.signal] > 0.4:
            self.subject.set_dimmer(frame[self.signal] * 255)
            self.subject.set_strobe(0)
        else:
            self.subject.set_dimmer(0)
            self.subject.set_strobe(0)
