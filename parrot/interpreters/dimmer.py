import math
import random
import scipy
from typing import List, TypeVar
from parrot.director.frame import FrameSignal
from parrot.fixtures.base import FixtureBase
from parrot.interpreters.base import InterpreterArgs, InterpreterBase
from parrot.utils.math import clamp


T = TypeVar("T", bound=FixtureBase)


class Dimmer255(InterpreterBase):
    def step(self, frame, scheme):
        for i in self.group:
            i.set_dimmer(255)


class Dimmer30(InterpreterBase):
    def step(self, frame, scheme):
        for i in self.group:
            i.set_dimmer(30)


class Dimmer0(InterpreterBase):
    def step(self, frame, scheme):
        for i in self.group:
            i.set_dimmer(0)


class DimmerFadeIn(InterpreterBase):
    def __init__(self, group: List[T], args: InterpreterArgs, fade_time=3):
        super().__init__(group, args)
        self.fade_time = fade_time
        self.memory = 0

    def step(self, frame, scheme):
        for i in self.group:
            self.memory = clamp(self.memory + 255 / (self.fade_time * 30), 0, 255)
            i.set_dimmer(self.memory)


class SequenceDimmers(InterpreterBase[T]):
    hype = 30

    def __init__(
        self, group: List[T], args: InterpreterArgs, dimmer=255, wait_time=0.5
    ):
        super().__init__(group, args)
        self.dimmer = dimmer
        self.wait_time = wait_time

    def step(self, frame, scheme):
        for i, fixture in enumerate(self.group):
            fixture.set_dimmer(
                self.dimmer
                if round(frame.time / self.wait_time) % len(self.group) == i
                else 0
            )


class SequenceFadeDimmers(InterpreterBase[T]):
    hype = 20

    def __init__(self, group: List[T], args: InterpreterArgs, wait_time=3):
        super().__init__(group, args)
        self.wait_time = wait_time

    def step(self, frame, scheme):
        for i, fixture in enumerate(self.group):
            fixture.set_dimmer(
                128
                + math.cos(
                    math.pi
                    * ((frame.time / self.wait_time) - (2 * i / len(self.group)))
                )
                * 128
            )


class DimmersBeatChase(InterpreterBase[T]):
    hype = 70

    def __init__(self, group: List[T], args: InterpreterArgs):
        super().__init__(group, args)
        self.signal = FrameSignal.freq_high
        self.on = False

    def step(self, frame, scheme):

        if frame[self.signal] > 0.4:
            if self.on == False:
                self.bulb = random.randint(0, len(self.group) - 1)
                self.on = True

            for idx, fixture in enumerate(self.group):
                if idx == self.bulb:
                    fixture.set_dimmer(frame[self.signal] * 255)
                else:
                    fixture.set_dimmer(0)

        else:
            for fixture in self.group:
                fixture.set_dimmer(0)
            self.on = False


class GentlePulse(InterpreterBase[T]):
    hype = 10

    def __init__(
        self,
        group: List[T],
        args: InterpreterArgs,
        signal=FrameSignal.freq_all,
        trigger_level=0.2,
    ):
        super().__init__(group, args)
        self.signal = signal
        self.on = False
        self.memory = [0] * len(self.group)
        self.trigger_level = trigger_level

    def step(self, frame, scheme):
        if frame[self.signal] > self.trigger_level:
            if self.on == False:
                self.bulb = random.randint(0, len(self.group) - 1)
                self.on = True

            self.memory[self.bulb] = max(self.memory[self.bulb], frame[self.signal])

        else:
            self.on = False

        for idx, fixture in enumerate(self.group):
            fixture.set_dimmer(self.memory[idx] * 255)
            self.memory[idx] *= 0.95


class Twinkle(InterpreterBase[T]):
    hype = 5

    def __init__(self, group: List[T], args: InterpreterArgs):
        super().__init__(group, args)
        self.memory = [0] * len(self.group)

    def step(self, frame, scheme):
        for idx, fixture in enumerate(self.group):
            if random.random() > 0.99:
                self.memory[idx] = 1

            fixture.set_dimmer(self.memory[idx] * 255)
            self.memory[idx] *= 0.9
