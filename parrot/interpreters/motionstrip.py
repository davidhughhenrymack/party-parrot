import math
import random
from typing import List
from parrot.director.frame import FrameSignal
from parrot.interpreters.base import InterpreterArgs, InterpreterBase, MoveCircles
from parrot.fixtures.motionstrip import Motionstrip38
from parrot.fixtures.base import FixtureBase
from parrot.interpreters.combo import combo
from parrot.utils.colour import Color
from parrot.utils.dmx_utils import clamp
from parrot.utils.lerp import lerp
from parrot.utils.color_extra import dim_color


class PanLatched(InterpreterBase[FixtureBase]):
    def __init__(
        self,
        group,
        args: InterpreterArgs,
        signal=FrameSignal.sustained_low,
        latch_level=0.3,
        latch_duration=math.pi * 2,
    ):
        super().__init__(group, args)
        self.signal = signal
        self.latch_level = latch_level
        self.latch_duration = latch_duration

        self.on = False
        self.on_time = 0

    def step(self, frame, scheme):
        if frame[self.signal] > self.latch_level and self.on == False:
            self.on = True
            self.on_time = frame.time

        if self.on:
            pan = -math.cos(frame.time - self.on_time) * 127 + 128

            if frame.time - self.on_time > self.latch_duration:
                self.on = False
                pan = 0
        else:
            pan = 0

        for fixture in self.group:
            fixture.set_pan(pan)


class MotionstripSlowRespond(InterpreterBase[Motionstrip38]):
    hype = 30

    def __init__(
        self,
        group: List[Motionstrip38],
        args: InterpreterArgs,
    ):
        super().__init__(group, args)
        self.signal = FrameSignal.sustained_low
        self.dimmer_memory = 0
        self.decay_rate = 0.24
        self.latch_until = 0

    def step(self, frame, scheme):
        pan = math.cos(frame.time) * 127 + 128

        if frame[self.signal] > 0.2:
            self.dimmer_memory = lerp(
                self.dimmer_memory, frame[self.signal] * 255, self.decay_rate
            )
        else:
            self.dimmer_memory = lerp(self.dimmer_memory, 0, self.decay_rate)

        for i in self.group:
            i.set_pan(pan)

            if self.latch_until > frame.time:
                self.render_bulb_chase(i, frame, scheme)
                i.set_dimmer(255)
            elif frame[self.signal] > 0.6:
                i.set_color(scheme.fg)
                for bulb in i.get_bulbs():
                    bulb.set_dimmer(255)
                i.set_dimmer(255 * math.sin(frame.time * 30))
            elif frame[self.signal] > 0.4:
                self.latch_until = frame.time + 0.5
                self.render_bulb_chase(i, frame, scheme)
                i.set_dimmer(255)
            else:
                i.set_color(scheme.fg)
                i.set_dimmer(self.dimmer_memory)
                for bulb in i.get_bulbs():
                    bulb.set_dimmer(255)

    def render_bulb_chase(self, motionstrip, frame, scheme):
        for idx, bulb in enumerate(motionstrip.get_bulbs()):
            color = Color("black")
            if int(frame.time * 10) % 8 == idx:
                color = scheme.fg
            bulb.set_color(color)
