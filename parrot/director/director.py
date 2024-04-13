import random
import time
import os
from typing import List
from parrot.director.frame import Frame, FrameSignal
from parrot.director.phrase_machine import PhraseMachine
from parrot.fixtures import laser

from parrot.patch_bay import patch_bay
from parrot.fixtures.led_par import LedPar
from parrot.fixtures.motionstrip import Motionstrip

from parrot.director.color_schemes import color_schemes

from parrot.interpreters.base import InterpreterArgs, InterpreterBase
from parrot.director.phrase import Phrase
from parrot.fixtures.laser import Laser
from parrot.fixtures.chauvet.rotosphere import ChauvetRotosphere_28Ch
from .phrase_interpretations import get_interpreter

from parrot.utils.lerp import LerpAnimator
from parrot.fixtures.moving_head import MovingHead
from parrot.state import State

SHIFT_AFTER = 60
WARMUP_SECONDS = max(int(os.environ.get("WARMUP_TIME", "40")), 1)


def filter_nones(l):
    return [i for i in l if i is not None]


class Director:
    def __init__(self, state: State):
        self.scheme = LerpAnimator(random.choice(color_schemes), 4)
        self.last_shift_time = time.time()
        self.shift_count = 0
        self.start_time = time.time()
        self.state = state

        self.phrase_machine = PhraseMachine(state)

        self.warmup_complete = False

        self.state.events.on_phrase_change += lambda s: self.generate_interpreters()
        self.state.events.on_hype_change += lambda s: self.generate_interpreters()
        self.state.events.on_theme_change += lambda s: self.shift()
        self.state.set_phrase(Phrase.general)

    def generate_interpreters(self):

        to_group = [LedPar, MovingHead, Motionstrip, Laser, ChauvetRotosphere_28Ch]
        fixture_groups = []

        for cls in to_group:
            fixtures = [i for i in patch_bay if isinstance(i, cls)]
            fixture_groups.append(fixtures)

        self.interpreters: List[InterpreterBase] = [
            get_interpreter(
                self.state.phrase,
                i,
                InterpreterArgs(self.state.hype, self.state.theme.allow_rainbows),
            )
            for i in fixture_groups
        ]

        print(f"Generated interpretation for {self.state.phrase}:")
        for i in self.interpreters:
            print(f"    {str(i)} {[str(j) for j in i.group]}")

        print()

    def generate_color_scheme(self):
        s = random.choice(self.state.theme.color_scheme)
        self.scheme.push(s)
        print(f"Shifting to {s}")

    def shift(self):
        self.generate_color_scheme()
        self.generate_interpreters()

        self.last_shift_time = time.time()
        self.shift_count += 1

    def step(self, frame: Frame):
        scheme = self.scheme.render()
        run_time = time.time() - self.start_time
        warmup_phase = min(1, run_time / WARMUP_SECONDS)

        if warmup_phase == 1 and not self.warmup_complete:
            print("Warmup phase complete")
            self.warmup_complete = True

        frame = frame * warmup_phase

        additional_signals = self.phrase_machine.step(frame)
        frame.extend(additional_signals)

        for i in self.interpreters:
            i.step(frame, scheme)

        if (
            time.time() - self.last_shift_time > SHIFT_AFTER
            and frame[FrameSignal.sustained_low] < 0.2
        ):
            self.shift()

    def render(self, dmx):
        for i in patch_bay:
            i.render(dmx)

        dmx.submit()
