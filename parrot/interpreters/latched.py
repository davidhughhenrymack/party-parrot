import random
from typing import List
from parrot.interpreters.base import InterpreterBase
from parrot.fixtures.base import FixtureBase
from parrot.utils.lerp import lerp


class DimmerBinaryLatched(InterpreterBase):
    def __init__(self, group: List[FixtureBase], signal="sustained"):
        super().__init__(group)
        self.signal = signal
        self.switch = False
        self.latch_until = 0

    def step(self, frame, scheme):
        for i in self.group:
            if frame["sustained"] > 0.55:
                self.switch = True
                self.latch_until = frame.time + 0.5
            elif frame["sustained"] < 0.2:
                self.switch = False

            if self.switch or self.latch_until > frame.time:
                i.set_dimmer(255)
            else:
                i.set_dimmer(0)


class DimmerFadeLatched(InterpreterBase):
    def __init__(self, group, signal="sustained"):
        super().__init__(group)
        self.signal = signal
        self.switch = False
        self.latch_until = 0
        self.memory = 0

    def step(self, frame, scheme):
        for i in self.group:
            if frame[self.signal] > 0.55:
                self.switch = True
                self.latch_until = frame.time + 0.5
            elif frame[self.signal] < 0.2:
                self.switch = False

            if self.switch or self.latch_until > frame.time:
                self.memory = lerp(self.memory, 255, 0.1)
                i.set_dimmer(self.memory)
            else:
                i.set_dimmer(0)


class DimmerFadeLatchedRandom(InterpreterBase):
    def __init__(
        self, group, signal="sustained", latch_at=0.55, latch_off_at=0.1, latch_time=0.5
    ):
        super().__init__(group)
        self.signal = signal
        self.switch = False
        self.latch_until = 0

        self.memory = 0

        self.selected = None
        self.latch_at = latch_at
        self.latch_off_at = latch_off_at
        self.latch_time = latch_time

    def step(self, frame, scheme):

        if frame[self.signal] > self.latch_at:
            self.switch = True
            self.latch_until = frame.time + self.latch_time
            if self.selected is None:
                self.selected = random.choice(self.group)
        elif frame[self.signal] < self.latch_off_at:
            self.switch = False

        if self.switch or self.latch_until > frame.time:
            self.memory = lerp(self.memory, 255, 0.1)
            self.selected.set_dimmer(self.memory)
        else:
            if self.selected is not None:
                self.selected.set_dimmer(0)
            self.selected = None
            self.memory = 0
