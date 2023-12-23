import random
import math
import time
from typing import List
from parrot.director.color_scheme import ColorScheme
from parrot.director.frame import Frame
from parrot.interpreters.led_par_group import LedParGroup, LedParSlowRespond
from parrot.interpreters.motionstrip import MotionstripWaveform

from parrot.patch.patch_bay import patch_bay
from parrot.patch.chauvet import ChauvetSpot160
from parrot.patch.led_par import LedPar
from parrot.patch.motionstrip import Motionstrip38
from parrot.director.schemes import color_schemes
from parrot.interpreters.movers import MoverBeat
from parrot.interpreters.base import InterpreterBase

SHIFT_AFTER = 3 * 60


class Director:
    def __init__(self):
        self.shift()

        pars = [i for i in patch_bay if isinstance(i, LedPar)]
        self.motionstrips = [i for i in patch_bay if isinstance(i, Motionstrip38)]
        self.movers = [i for i in patch_bay if isinstance(i, ChauvetSpot160)]

        self.interpreters: List[InterpreterBase] = [
            LedParSlowRespond(LedParGroup(pars)),
            *[MotionstripWaveform(i) for i in self.motionstrips],
            *[MoverBeat(i) for i in self.movers],
        ]

    def shift(self):
        self.scheme = random.choice(color_schemes)
        self.last_shift_time = time.time()

    def step(self, frame: Frame):
        for i in self.interpreters:
            i.step(frame, self.scheme)

        if time.time() - self.last_shift_time > SHIFT_AFTER:
            self.shift()

    def render(self, dmx):
        for i in patch_bay:
            i.render(dmx)

        dmx.submit()
