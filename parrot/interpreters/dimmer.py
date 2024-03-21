import random
import scipy
from typing import List, TypeVar
from parrot.fixtures.base import FixtureBase
from parrot.interpreters.base import InterpreterBase


T = TypeVar("T", bound=FixtureBase)


class Dimmer100(InterpreterBase):
    def step(self, frame, scheme):
        for i in self.group:
            i.set_dimmer(100)


class Dimmer30(InterpreterBase):
    def step(self, frame, scheme):
        for i in self.group:
            i.set_dimmer(30)


class Dimmer0(InterpreterBase):
    def step(self, frame, scheme):
        for i in self.group:
            i.set_dimmer(0)


class SequenceDimmers(InterpreterBase[T]):
    def __init__(self, group: List[T], dimmer=255, wait_time=60 * 2 / 120):
        super().__init__(group)
        self.dimmer = dimmer
        self.wait_time = wait_time

    def step(self, frame, scheme):
        for i, fixture in enumerate(self.group):
            fixture.set_dimmer(
                self.dimmer
                if round(frame.time / self.wait_time) % len(self.group) == i
                else 0
            )


class DimmersBeatChase(InterpreterBase[T]):
    def __init__(self, group: List[T]):
        super().__init__(group)
        self.signal = "drums"
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
    def __init__(self, group: List[T], signal="all"):
        super().__init__(group)
        self.signal = signal
        self.on = False
        self.memory = [0] * len(self.group)

    def step(self, frame, scheme):
        if frame[self.signal] > 0.2:
            if self.on == False:
                self.bulb = random.randint(0, len(self.group) - 1)
                self.on = True

            self.memory[self.bulb] = max(self.memory[self.bulb], frame[self.signal])

        else:
            self.on = False

        for idx, fixture in enumerate(self.group):
            fixture.set_dimmer(self.memory[idx] * 255)
            self.memory[idx] *= 0.95
