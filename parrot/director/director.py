import random
import math
import time
from typing import List
from parrot.director.color_scheme import ColorScheme
from parrot.director.frame import Frame
from parrot.interpreters.led_par_group import LedParGroup, LedParSlowRespond
from parrot.interpreters.motionstrip import MotionstripSlowRespond, MotionstripWaveform

from parrot.patch_bay import patch_bay
from parrot.fixtures.chauvet import ChauvetSpot160
from parrot.fixtures.led_par import LedPar
from parrot.fixtures.motionstrip import Motionstrip38
from parrot.director.color_schemes import color_schemes
from parrot.interpreters.movers import MoverBeat
from parrot.interpreters.base import InterpreterBase
from parrot.utils.lerp import LerpAnimator
from parrot.fixtures.uking.laser import FiveBeamLaser
from parrot.interpreters.latched import DimmerBinaryLatched
from parrot.fixtures.oultia.laser import TwoBeamLaser

SHIFT_AFTER = 2 * 60

interpreters = {
    Motionstrip38: MotionstripSlowRespond,
    ChauvetSpot160: MoverBeat,
    FiveBeamLaser: DimmerBinaryLatched,
    TwoBeamLaser: DimmerBinaryLatched,
}


def get_interpreter(f):
    for k, v in interpreters.items():
        if isinstance(f, k):
            return v(f)
    return None


def filter_nones(l):
    return [i for i in l if i is not None]


class Director:
    def __init__(self):
        self.scheme = LerpAnimator(random.choice(color_schemes), 4)
        self.last_shift_time = time.time()

        pars = [i for i in patch_bay if isinstance(i, LedPar)]
        inferred = [get_interpreter(i) for i in patch_bay]

        self.interpreters: List[InterpreterBase] = [
            LedParSlowRespond(LedParGroup(pars)),
        ] + filter_nones(inferred)

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
