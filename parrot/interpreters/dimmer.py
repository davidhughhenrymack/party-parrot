import math
import random
import scipy
from typing import TypeVar
from beartype import beartype
from parrot.director.frame import FrameSignal
from parrot.fixtures.base import FixtureBase
from parrot.interpreters.base import InterpreterArgs, InterpreterBase
from parrot.utils.math import clamp


T = TypeVar("T", bound=FixtureBase)


@beartype
class Dimmer255(InterpreterBase):
    def step(self, frame, scheme):
        for i in self.group:
            i.set_dimmer(255)


@beartype
class Dimmer30(InterpreterBase):
    def step(self, frame, scheme):
        for i in self.group:
            i.set_dimmer(30)


@beartype
class Dimmer0(InterpreterBase):
    def step(self, frame, scheme):
        for i in self.group:
            i.set_dimmer(0)
            i.set_strobe(0)


@beartype
class DimmerFadeIn(InterpreterBase):
    def __init__(self, group: list[T], args: InterpreterArgs, fade_time=3):
        super().__init__(group, args)
        self.fade_time = fade_time
        self.memory = 0

    def step(self, frame, scheme):
        for i in self.group:
            self.memory = clamp(self.memory + 255 / (self.fade_time * 30), 0, 255)
            i.set_dimmer(self.memory)


@beartype
class SequenceDimmers(InterpreterBase[T]):
    hype = 30

    def __init__(self, group: list[T], args: InterpreterArgs, dimmer=255, wait_time=1):
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


@beartype
class SequenceFadeDimmers(InterpreterBase[T]):
    hype = 20

    def __init__(self, group: list[T], args: InterpreterArgs, wait_time=3):
        super().__init__(group, args)
        self.wait_time = wait_time

    def step(self, frame, scheme):
        for i, fixture in enumerate(self.group):
            # Use a power function to spend more time at low values
            raw_cos = math.cos(
                math.pi * ((frame.time / self.wait_time) - (2 * i / len(self.group)))
            )
            # Map -1 to 1 range to 0 to 1, then apply power to create more low values
            normalized = ((raw_cos + 1) / 2) ** 4
            # Scale back to 0-255 range
            fixture.set_dimmer(normalized * 255)


@beartype
class DimmersBeatChase(InterpreterBase[T]):
    hype = 75

    def __init__(self, group: list[T], args: InterpreterArgs):
        super().__init__(group, args)
        self.signal = random.choice([FrameSignal.freq_high, FrameSignal.freq_low])
        self.on = False

    def step(self, frame, scheme):

        if frame[self.signal] > 0.3:
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


@beartype
class GentlePulse(InterpreterBase[T]):
    hype = 10

    def __init__(
        self,
        group: list[T],
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


@beartype
class StabPulse(InterpreterBase[T]):
    hype = 50

    def __init__(
        self,
        group: list[T],
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
            self.memory[idx] *= 0.5


@beartype
class LightingStab(InterpreterBase[T]):
    hype = 60

    def __init__(
        self,
        group: list[T],
        args: InterpreterArgs,
        trigger_level=0.2,
    ):
        super().__init__(group, args)
        from parrot.utils.colour import Color

        self.white = Color("white")
        self.on_low = False
        self.on_high = False
        self.memory = [0] * len(self.group)
        self.trigger_level = trigger_level
        self.strobe_memory = [0] * len(self.group)

    def step(self, frame, scheme):
        # Handle freq_low - existing stab behavior
        if frame[FrameSignal.freq_low] > self.trigger_level:
            if self.on_low == False:
                self.bulb = random.randint(0, len(self.group) - 1)
                self.on_low = True

            self.memory[self.bulb] = max(
                self.memory[self.bulb], frame[FrameSignal.freq_low]
            )
        else:
            self.on_low = False

        # Handle freq_high - white brief strobe
        if frame[FrameSignal.freq_high] > self.trigger_level:
            if self.on_high == False:
                self.strobe_bulb = random.randint(0, len(self.group) - 1)
                self.on_high = True

            self.strobe_memory[self.strobe_bulb] = 1.0
        else:
            self.on_high = False

        # Apply effects to fixtures
        for idx, fixture in enumerate(self.group):
            # If strobe is active, set white and brightness based on strobe_memory
            if self.strobe_memory[idx] > 0:
                fixture.set_color(self.white)
                fixture.set_dimmer(self.strobe_memory[idx] * 255)
                fixture.set_strobe(220)
                self.strobe_memory[idx] *= 0.5  # Fast decay for brief strobe
            else:
                # Otherwise use normal stab effect
                fixture.set_dimmer(self.memory[idx] * 255)
                fixture.set_strobe(0)

            self.memory[idx] *= 0.5


@beartype
class Twinkle(InterpreterBase[T]):
    hype = 5

    def __init__(self, group: list[T], args: InterpreterArgs):
        super().__init__(group, args)
        self.memory = [0] * len(self.group)

    def step(self, frame, scheme):
        for idx, fixture in enumerate(self.group):

            if random.random() > 0.99:
                self.memory[idx] = 1

            fixture.set_dimmer(self.memory[idx] * 255)
            self.memory[idx] *= 0.9
