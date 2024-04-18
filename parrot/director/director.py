import random
import time
import os
from typing import List
from parrot.director.frame import Frame, FrameSignal
from parrot.director.phrase_machine import PhraseMachine
from parrot.fixtures import laser

from parrot.patch_bay import venue_patches
from parrot.fixtures.led_par import LedPar
from parrot.fixtures.motionstrip import Motionstrip

from parrot.director.color_schemes import color_schemes
from parrot.director.color_scheme import ColorScheme

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

HYPE_BUCKETS = [10, 40, 70]


def filter_nones(l):
    return [i for i in l if i is not None]


class Director:
    def __init__(self, state: State):
        self.scheme = LerpAnimator(random.choice(color_schemes), 4)
        self.last_shift_time = time.time()
        self.shift_count = 0
        self.start_time = time.time()
        self.state = state

        self.state.set_phrase(Phrase.general)

        self.setup_patch()
        self.generate_color_scheme()
        self.phrase_machine = PhraseMachine(state)

        self.warmup_complete = False

        # self.state.events.on_phrase_change += lambda s: self.generate_interpreters()
        # self.state.events.on_hype_change += lambda s: self.generate_interpreters()
        self.state.events.on_theme_change += lambda s: self.generate_color_scheme()
        self.state.events.on_venue_change += lambda s: self.setup_patch()

    def setup_patch(self):
        self.group_fixtures()
        self.generate_interpreters()

    def group_fixtures(self):
        to_group = [LedPar, MovingHead, Motionstrip, Laser, ChauvetRotosphere_28Ch]
        self.fixture_groups = []

        for cls in to_group:
            fixtures = [
                i for i in venue_patches[self.state.venue] if isinstance(i, cls)
            ]
            if len(fixtures) > 0:
                self.fixture_groups.append(fixtures)

    def generate_interpreters(self):
        self.interpreters: List[InterpreterBase] = [
            get_interpreter(
                self.state.phrase,
                group,
                InterpreterArgs(
                    HYPE_BUCKETS[idx % len(HYPE_BUCKETS)],
                    self.state.theme.allow_rainbows,
                ),
            )
            for idx, group in enumerate(self.fixture_groups)
        ]

        print(f"Generated interpretation for {self.state.phrase}:")
        for i in self.interpreters:
            print(f"    {str(i)} {[str(j) for j in i.group]} hype={i.get_hype()}")

        print()

    def generate_color_scheme(self):
        s = random.choice(self.state.theme.color_scheme)
        self.scheme.push(s)
        print(f"Shifting to {s}")

    def shift_color_scheme(self):
        s = random.choice(self.state.theme.color_scheme)
        st = s.to_list()
        ct = self.scheme.render().to_list()
        idx = random.randint(0, 2)
        ct[idx] = st[idx]
        self.scheme.push(ColorScheme.from_list(ct))

    def shift_interpreter(self):
        eviction_index = random.randint(0, len(self.interpreters) - 1)
        eviction_group = self.fixture_groups[eviction_index]

        hype_counts = {key: 0 for key in HYPE_BUCKETS}

        for idx, i in enumerate(self.interpreters):
            if idx != eviction_index:
                hype = i.get_hype()
                bucket = sorted(
                    [(bucket, abs(hype - bucket)) for bucket in HYPE_BUCKETS],
                    key=lambda i: i[1],
                )[0][0]
                hype_counts[bucket] += 1

        smallest_bucket = sorted(hype_counts.items(), key=lambda i: i[1])[0][0]

        self.interpreters[eviction_index] = get_interpreter(
            self.state.phrase,
            eviction_group,
            InterpreterArgs(smallest_bucket, self.state.theme.allow_rainbows),
        )

        print(
            f"Shifted interpretation for {self.state.phrase} hype_goal={smallest_bucket}:"
        )
        print(
            f"    {str(self.interpreters[eviction_index] )} {[str(j) for j in eviction_group]} hype={self.interpreters[eviction_index].get_hype()}"
        )

    def shift(self):
        self.shift_color_scheme()
        self.shift_interpreter()

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
            for i in self.interpreters:
                i.exit(frame, scheme)
            self.shift()

    def render(self, dmx):
        for i in venue_patches[self.state.venue]:
            i.render(dmx)

        dmx.submit()
