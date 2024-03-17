import math
import random
from typing import List
from parrot.interpreters.base import GroupInterpreterBase, InterpreterBase, MoveCircles
from parrot.fixtures.motionstrip import Motionstrip38
from parrot.interpreters.combo import GroupCombo
from parrot.interpreters.group import groupify
from parrot.utils.colour import Color
from parrot.utils.dmx_utils import clamp
from parrot.utils.lerp import lerp


class MotionstripBulbBeat(GroupInterpreterBase[Motionstrip38]):
    def __init__(self, group: List[Motionstrip38]):
        super().__init__(group)
        self.signal = "drums"
        self.total_bulbs = len(group) * 8
        self.bulb = 0
        self.on = False

    def step(self, frame, scheme):
        if frame[self.signal] > 0.4:
            if self.on == False:
                self.bulb = random.randint(0, self.total_bulbs - 1)
            self.on = True

            for idx, fixture in enumerate(self.group):
                for bulb_idx in range(8):
                    color = Color("black")
                    absolute_idx = idx * 8 + bulb_idx
                    if absolute_idx == self.bulb:
                        color = scheme.fg

                    fixture.set_bulb_color(bulb_idx, color)

        else:
            if self.on == True:
                for fixture in self.group:
                    fixture.set_color(Color("black"))
            self.on = False


MotionStripBulbBeatAndWiggle = lambda group: GroupCombo(
    group, [MotionstripBulbBeat, groupify(MoveCircles)]
)


class MotionstripWaveform(InterpreterBase[Motionstrip38]):
    def __init__(self, subject: Motionstrip38):
        super().__init__(subject)
        self.signal = "vocals"

    def step(self, frame, scheme):
        color = scheme.fg
        parts = 4
        self.subject.set_dimmer(255)

        self.subject.set_pan(math.cos(frame.time) * 127 + 128)

        for i in range(parts):
            low = i * 1 / parts
            value = clamp(frame[self.signal] - low, 0, 1 / parts) * parts

            cc = Color(color)
            cc.set_rgb((cc.red * value, cc.green * value, cc.blue * value))
            self.subject.set_bulb_color(3 - i, cc)
            self.subject.set_bulb_color(i + 4, cc)


class MotionstripSlowRespond(InterpreterBase[Motionstrip38]):
    def __init__(self, subject: Motionstrip38):
        super().__init__(subject)
        self.signal = "sustained"
        self.dimmer_memory = 0
        self.decay_rate = 0.24
        self.latch_until = 0

    def step(self, frame, scheme):
        pan = math.cos(frame.time) * 127 + 128
        self.subject.set_pan(pan)

        if frame[self.signal] > 0.2:
            self.dimmer_memory = lerp(
                self.dimmer_memory, frame[self.signal] * 255, self.decay_rate
            )
        else:
            self.dimmer_memory = lerp(self.dimmer_memory, 0, self.decay_rate)

        # print(self.dimmer_memory)

        if self.latch_until > frame.time:
            self.render_bulb_chase(frame, scheme)
            self.subject.set_dimmer(255)
        elif frame[self.signal] > 0.6:
            self.subject.set_color(scheme.fg)
            self.subject.set_dimmer(255 * math.sin(frame.time * 30))
        elif frame[self.signal] > 0.4:
            self.latch_until = frame.time + 0.5
            self.render_bulb_chase(frame, scheme)
            self.subject.set_dimmer(255)
        else:
            self.subject.set_color(scheme.fg)
            self.subject.set_dimmer(self.dimmer_memory)

    def render_bulb_chase(self, frame, scheme):
        for i in range(8):
            color = Color("black")
            if int(frame.time * 10) % 8 == i:
                color = scheme.fg
            self.subject.set_bulb_color(i, color)
