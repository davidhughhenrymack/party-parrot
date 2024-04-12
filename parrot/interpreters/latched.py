import random
from typing import List
from parrot.director.frame import FrameSignal
from parrot.interpreters.base import InterpreterArgs, InterpreterBase, with_args
from parrot.fixtures.base import FixtureBase
from parrot.utils.lerp import lerp


class DimmerBinaryLatched(InterpreterBase):
    hype = 40

    def __init__(
        self,
        group: List[FixtureBase],
        args: InterpreterArgs,
        signal=FrameSignal.sustained_low,
    ):
        super().__init__(group, args)
        self.signal = signal
        self.switch = False
        self.latch_until = 0

    def step(self, frame, scheme):
        for i in self.group:
            if frame[FrameSignal.sustained_low] > 0.55:
                self.switch = True
                self.latch_until = frame.time + 0.5
            elif frame[FrameSignal.sustained_low] < 0.2:
                self.switch = False

            if self.switch or self.latch_until > frame.time:
                i.set_dimmer(255)
            else:
                i.set_dimmer(0)


class DimmerFadeLatched(InterpreterBase):
    hype = 40

    def __init__(
        self,
        group,
        args: InterpreterArgs,
        signal=FrameSignal.sustained_low,
        latch_time=0.5,
        condition_on=lambda x: x > 0.55,
        condition_off=lambda x: x < 0.2,
        fade_in_rate=0.1,
        fade_out_rate=0.1,
    ):
        super().__init__(group, args)
        self.signal = signal
        self.condition_on = condition_on
        self.condition_off = condition_off
        self.latch_time = latch_time
        self.fade_in_rate = fade_in_rate
        self.fade_out_rate = fade_out_rate

        self.switch = False
        self.latch_until = 0
        self.memory = 0

    def step(self, frame, scheme):
        for i in self.group:
            if self.condition_on(frame[self.signal]):
                self.switch = True
                self.latch_until = frame.time + self.latch_time
            elif self.condition_off(frame[self.signal]):
                self.switch = False

            if self.switch or self.latch_until > frame.time:
                self.memory = lerp(self.memory, 255, self.fade_in_rate)
            else:
                self.memory = lerp(self.memory, 0, self.fade_out_rate)
            i.set_dimmer(self.memory)


DimmerFadeLatched4s = with_args(
    DimmerFadeLatched, new_hype=5, new_has_rainbow=False, latch_time=4
)


class DimmerFadeLatchedRandom(InterpreterBase):
    hype = 50

    def __init__(
        self,
        group,
        args: InterpreterArgs,
        signal=FrameSignal.sustained_low,
        latch_at=0.55,
        latch_off_at=0.1,
        latch_time=0.5,
    ):
        super().__init__(group, args)
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
