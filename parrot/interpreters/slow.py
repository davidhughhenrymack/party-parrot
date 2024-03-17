import parrot.fixtures
from typing import List
from parrot.director.frame import Frame
from parrot.fixtures.led_par import LedPar
from parrot.interpreters.base import GroupInterpreterBase, InterpreterBase, Phrase
from parrot.utils.lerp import lerp
from parrot.director.color_scheme import ColorScheme
import math
import time
from parrot.fixtures.base import FixtureBase


class GroupSlowRespond(GroupInterpreterBase[FixtureBase]):
    def __init__(self, group):
        super().__init__(group)
        self.dimmer_memory = 0
        self.signal = "sustained"

    def step(self, frame: Frame, scheme: ColorScheme):
        self.dimmer_memory = lerp(self.dimmer_memory, frame.all, 0.24)

        for idx, fixture in enumerate(self.group):
            if idx % 2 == 0:
                fixture.set_color(scheme.bg)
            else:
                fixture.set_color(scheme.bg_contrast)

            if frame[self.signal] > 0.65:
                fixture.set_strobe(200)
            if frame[self.signal] > 0.5:
                fixture.set_dimmer(
                    50
                    + (255 - 50)
                    * math.sin(time.time() * 5 + math.pi * idx / len(self.group))
                )
                fixture.set_strobe(0)
            else:
                fixture.set_dimmer(self.dimmer_memory * 255)
                fixture.set_strobe(0)

    @classmethod
    def category(cls):
        return [Phrase.intro_outro]


class GroupSlowDecay(GroupInterpreterBase[FixtureBase]):
    def __init__(self, group):
        super().__init__(group)
        self.dimmer_memory = 0

    def step(self, frame: Frame, scheme: ColorScheme):
        self.dimmer_memory = max(lerp(self.dimmer_memory, 0, 0.1), frame.all)

        for idx, fixture in enumerate(self.group):
            if idx % 2 == 0:
                fixture.set_color(scheme.bg)
            else:
                fixture.set_color(scheme.bg_contrast)

            fixture.set_dimmer(self.dimmer_memory * 255)

    @classmethod
    def category(cls):
        return [Phrase.intro_outro]
