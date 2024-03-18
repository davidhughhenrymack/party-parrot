import random
import time
import os
from typing import List
from parrot.director.frame import Frame

from parrot.patch_bay import patch_bay
from parrot.fixtures.chauvet import ChauvetSpot160_12Ch, ChauvetSpot120_12Ch
from parrot.fixtures.led_par import LedPar
from parrot.fixtures.motionstrip import Motionstrip38

from parrot.director.color_schemes import color_schemes


from parrot.interpreters.movers import MoverBeatAndCircle
from parrot.interpreters.base import InterpreterBase
from parrot.interpreters.slow import GroupSlowRespond
from parrot.interpreters.motionstrip import MotionstripSlowRespond
from parrot.interpreters.latched import DimmerBinaryLatched


from parrot.utils.lerp import LerpAnimator
from parrot.fixtures.uking.laser import FiveBeamLaser
from parrot.fixtures.oultia.laser import TwoBeamLaser

SHIFT_AFTER = 2 * 60
WARMUP_SECONDS = max(int(os.environ.get("WARMUP_TIME", "40")), 1)
MAX_INTENSITY = 1

interpreters = {
    Motionstrip38: MotionstripSlowRespond,
    ChauvetSpot160_12Ch: MoverBeatAndCircle,
    ChauvetSpot120_12Ch: MoverBeatAndCircle,
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
        self.start_time = time.time()

        self.warmup_complete = False

        pars = [i for i in patch_bay if isinstance(i, LedPar)]
        inferred = [get_interpreter(i) for i in patch_bay]

        self.interpreters: List[InterpreterBase] = [
            GroupSlowRespond(pars),
        ] + filter_nones(inferred)

    def shift(self):
        s = random.choice(color_schemes)
        self.scheme.push(s)
        self.last_shift_time = time.time()

    def step(self, frame: Frame):
        scheme = self.scheme.render()

        run_time = time.time() - self.start_time
        warmup_phase = min(1, run_time / WARMUP_SECONDS)

        if warmup_phase == 1 and not self.warmup_complete:
            print("Warmup phase complete")
            self.warmup_complete = True

        throttled_frame = frame * warmup_phase * MAX_INTENSITY

        for i in self.interpreters:
            i.step(throttled_frame, scheme)

        if (
            time.time() - self.last_shift_time > SHIFT_AFTER
            and throttled_frame["sustained"] < 0.3
        ):
            self.shift()

    def render(self, dmx):
        for i in patch_bay:
            i.render(dmx)

        dmx.submit()
