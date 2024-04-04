from enum import Enum
import math
from typing import Generic, List, TypeVar
from parrot.director.frame import Frame
from parrot.fixtures.base import FixtureBase
from parrot.director.color_scheme import ColorScheme
from parrot.utils.colour import Color

T = TypeVar("T", bound=FixtureBase)


class InterpreterBase(Generic[T]):
    def __init__(self, group: List[T]):
        self.group = group

    def step(self, frame: Frame, scheme: ColorScheme):
        pass

    def __str__(self) -> str:
        return f"{self.__class__.__name__} {[str(i) for i in self.group]}"


class Noop(InterpreterBase):
    def step(self, frame, scheme):
        pass


class ColorFg(InterpreterBase):
    def step(self, frame, scheme):
        for i in self.group:
            i.set_color(scheme.fg)


class ColorAlternateBg(InterpreterBase):
    def step(self, frame, scheme):
        for idx, fixture in enumerate(self.group):
            fixture.set_color(scheme.bg if idx % 2 == 0 else scheme.bg_contrast)


class MoveCircles(InterpreterBase):
    def __init__(self, group: List[FixtureBase], multiplier=1, phase=math.pi):
        super().__init__(group)
        self.multiplier = multiplier
        self.phase = phase

    def step(self, frame, scheme):
        for idx, fixture in enumerate(self.group):
            fixture.set_pan(
                math.cos(frame.time * self.multiplier + self.phase * idx) * 127 + 128
            )
            fixture.set_tilt(
                math.sin(frame.time * self.multiplier + self.phase * idx) * 127 + 128
            )


class FlashBeat(InterpreterBase):
    def __init__(self, group):
        super().__init__(group)
        self.signal = "drums"

    def step(self, frame, scheme):
        for i in self.group:
            if frame["sustained"] > 0.7:
                i.set_dimmer(100)
                i.set_strobe(200)
            elif frame[self.signal] > 0.4:
                i.set_dimmer(frame[self.signal] * 255)
                i.set_strobe(0)
            else:
                i.set_dimmer(0)
                i.set_strobe(0)
