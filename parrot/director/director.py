import random
import math
import time
from typing import List
from parrot.director.color_scheme import ColorScheme
from parrot.director.frame import Frame
from parrot.interpreters.led_par_group import LedParGroup, LedParSlowRespond
from parrot.interpreters.motionstrip import MotionstripSlowRespond, MotionstripWaveform

from parrot.patch.patch_bay import patch_bay
from parrot.patch.chauvet import ChauvetSpot160
from parrot.patch.led_par import LedPar
from parrot.patch.motionstrip import Motionstrip38
from parrot.director.color_schemes import color_schemes
from parrot.interpreters.movers import MoverBeat
from parrot.interpreters.base import InterpreterBase
from parrot.utils.lerp import LerpAnimator

SHIFT_AFTER = 2 * 60


class Director:
    def __init__(self):
        self.scheme = LerpAnimator(random.choice(color_schemes), 4)
        self.last_shift_time = time.time()

        pars = [i for i in patch_bay if isinstance(i, LedPar)]
        self.motionstrips = [i for i in patch_bay if isinstance(i, Motionstrip38)]
        self.movers = [i for i in patch_bay if isinstance(i, ChauvetSpot160)]

        self.interpreters: List[InterpreterBase] = [
            LedParSlowRespond(LedParGroup(pars)),
            *[MotionstripSlowRespond(i) for i in self.motionstrips],
            *[MoverBeat(i) for i in self.movers],
        ]

    def shift(self):
        s = random.choice(color_schemes)
        self.scheme.push(s)
        self.last_shift_time = time.time()

    def step(self, frame: Frame):
        scheme = self.scheme.render()
        for i in self.interpreters:
            i.step(frame, scheme)

        if (
            time.time() - self.last_shift_time > SHIFT_AFTER
            and frame["sustained"] < 0.3
        ):
            self.shift()

    def render(self, dmx):
        for i in patch_bay:
            i.render(dmx)

        dmx.submit()
