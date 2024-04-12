import parrot.fixtures
from typing import List
from parrot.director.frame import Frame, FrameSignal
from parrot.interpreters.base import InterpreterArgs, InterpreterBase, with_args

from parrot.utils.lerp import lerp
from parrot.director.color_scheme import ColorScheme
import math
import time
from parrot.fixtures.base import FixtureBase


class SlowRespond(InterpreterBase[FixtureBase]):
    hype = 25

    def __init__(
        self,
        group,
        args: InterpreterArgs,
    ):
        super().__init__(group, args)
        self.dimmer_memory = 0
        self.signal = FrameSignal.sustained_low

    def step(self, frame: Frame, scheme: ColorScheme):
        self.dimmer_memory = lerp(self.dimmer_memory, frame.all, 0.24)

        for idx, fixture in enumerate(self.group):
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


class SlowDecay(InterpreterBase[FixtureBase]):
    hype = 20

    def __init__(self, group, args: InterpreterArgs, decay_rate=0.1):
        super().__init__(group, args)
        self.dimmer_memory = 0
        self.decay_rate = decay_rate

    def step(self, frame: Frame, scheme: ColorScheme):
        self.dimmer_memory = max(
            lerp(self.dimmer_memory, 0, self.decay_rate), frame.all
        )

        for fixture in self.group:
            fixture.set_dimmer(self.dimmer_memory * 255)


VerySlowDecay = with_args(SlowDecay, new_hype=5, new_has_rainbow=False, decay_rate=0.01)
