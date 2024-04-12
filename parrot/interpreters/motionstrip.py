import math
import random
from typing import List
from parrot.director.frame import FrameSignal
from parrot.interpreters.base import InterpreterArgs, InterpreterBase, MoveCircles
from parrot.fixtures.motionstrip import Motionstrip38
from parrot.interpreters.combo import combo
from parrot.utils.colour import Color
from parrot.utils.dmx_utils import clamp
from parrot.utils.lerp import lerp
from parrot.utils.color_extra import dim_color


class MotionstripBulbBeat(InterpreterBase[Motionstrip38]):
    hype = 60

    def __init__(
        self,
        group: List[Motionstrip38],
        args: InterpreterArgs,
    ):
        super().__init__(group, args)
        self.signal = FrameSignal.freq_high
        self.total_bulbs = len(group) * 8
        self.bulb = 0
        self.on = False

    def step(self, frame, scheme):

        if frame[self.signal] > 0.4:
            if self.on == False:
                self.bulb = random.randint(0, self.total_bulbs - 1)
            self.on = True

            for idx, fixture in enumerate(self.group):
                for bulb_idx, bulb in enumerate(fixture.get_bulbs()):
                    color = Color("black")
                    absolute_idx = idx * 8 + bulb_idx
                    if absolute_idx == self.bulb:
                        color = scheme.fg

                    bulb.set_color(color)
                fixture.set_dimmer(frame[self.signal] * 255)

        else:
            for fixture in self.group:
                fixture.set_dimmer(0)
            self.on = False


MotionStripBulbBeatAndWiggle = combo(MotionstripBulbBeat, MoveCircles)


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
