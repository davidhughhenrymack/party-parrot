import parrot.fixtures
import scipy
from typing import List
from parrot.director.frame import Frame, FrameSignal
from parrot.interpreters.base import InterpreterArgs, InterpreterBase, with_args

from parrot.utils.lerp import lerp
from parrot.director.color_scheme import ColorScheme
import math
import time
from parrot.fixtures.base import FixtureBase


class SlowDecay(InterpreterBase[FixtureBase]):
    hype = 20

    def __init__(
        self,
        group,
        args: InterpreterArgs,
        decay_rate=0.1,
        signal=FrameSignal.freq_all,
        signal_fn=lambda x: x,
    ):
        super().__init__(group, args)
        self.dimmer_memory = 0
        self.decay_rate = decay_rate
        self.signal = signal
        self.signal_fn = signal_fn

    def step(self, frame: Frame, scheme: ColorScheme):
        self.dimmer_memory = max(
            lerp(self.dimmer_memory, 0, self.decay_rate),
            self.signal_fn(frame[self.signal]),
        )

        for fixture in self.group:
            fixture.set_dimmer(self.dimmer_memory * 255)


VerySlowDecay = with_args(
    "VerySlowDecay", SlowDecay, new_hype=5, new_has_rainbow=False, decay_rate=0.01
)
SlowSustained = with_args(
    "SlowSustained",
    SlowDecay,
    new_hype=5,
    new_has_rainbow=False,
    decay_rate=0.5,
    signal=FrameSignal.sustained_low,
)

OnWhenNoSustained = with_args(
    "OnWhenNoSustained",
    SlowDecay,
    new_hype=0,
    new_has_rainbow=False,
    decay_rate=0.01,
    signal=FrameSignal.sustained_low,
    signal_fn=lambda x: 1 - x,
)
