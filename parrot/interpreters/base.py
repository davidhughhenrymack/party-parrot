from collections import namedtuple
from enum import Enum
import math
from typing import Generic, List, TypeVar
from parrot.director.frame import Frame
from parrot.fixtures.base import FixtureBase
from parrot.director.color_scheme import ColorScheme
from parrot.utils.colour import Color

T = TypeVar("T", bound=FixtureBase)

InterpreterArgs = namedtuple("InterpreterArgs", ["hype", "allow_rainbows"])


class InterpreterBase(Generic[T]):
    has_rainbow = False
    hype = 0

    def __init__(self, group: List[T], args: InterpreterArgs):
        self.group = group
        self.interpreter_args = args

    def step(self, frame: Frame, scheme: ColorScheme):
        pass

    @classmethod
    def acceptable(cls, args: InterpreterArgs) -> bool:
        if cls.has_rainbow and not args.allow_rainbows:
            return False

        if cls.hype > args.hype:
            return False

        return True

    def __str__(self) -> str:
        return f"{self.__class__.__name__}"


def with_args(interpreter, new_hype=None, new_has_rainbow=None, **kwargs):

    class WithArgs(InterpreterBase):
        def __init__(self, group, args):
            super().__init__(group, args)
            self.interpreter = interpreter(group, args, **kwargs)

        @classmethod
        def acceptable(cls, args):
            if new_hype is not None and new_has_rainbow is not None:
                if new_hype > args.hype:
                    return False
                if new_has_rainbow and not args.allow_rainbows:
                    return False
                return True
            return interpreter.acceptable(args)

        def step(self, frame, scheme):
            self.interpreter.step(frame, scheme)

        def __str__(self):
            return str(self.interpreter)

    return WithArgs


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


class ColorBg(InterpreterBase):
    def step(self, frame, scheme):
        for idx, fixture in enumerate(self.group):
            fixture.set_color(scheme.bg)


class ColorRainbow(InterpreterBase):
    has_rainbow = True

    def __init__(self, group, args, color_speed=0.08, color_phase_spread=0.2):
        super().__init__(group, args)
        self.color_speed = color_speed
        self.color_phase_spread = color_phase_spread

    def step(self, frame, scheme):
        for idx, fixture in enumerate(self.group):
            color = Color("red")
            phase = (
                frame.time * self.color_speed
                + self.color_phase_spread / len(self.group) * idx
            )
            color.set_hue(phase - math.floor(phase))
            fixture.set_color(color)


class MoveCircles(InterpreterBase):
    def __init__(self, group: List[FixtureBase], args, multiplier=1, phase=math.pi):
        super().__init__(group, args)
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


class MoveNod(InterpreterBase):
    def __init__(self, group: List[FixtureBase], args, multiplier=1, phase=math.pi / 3):
        super().__init__(group, args)
        self.multiplier = multiplier
        self.phase = phase

    def step(self, frame, scheme):
        for idx, fixture in enumerate(self.group):
            fixture.set_pan(0)
            fixture.set_tilt(
                math.sin(frame.time * self.multiplier + self.phase * idx) * 127 + 128
            )


class FlashBeat(InterpreterBase):
    hype = 70

    def __init__(self, group, args):
        super().__init__(group, args)
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
