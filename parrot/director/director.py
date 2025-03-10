import random
import time
import os
from typing import List
from parrot.director.frame import Frame, FrameSignal
from parrot.director.phrase_machine import PhraseMachine
from parrot.fixtures import laser

from parrot.patch_bay import venue_patches, get_manual_group
from parrot.fixtures.led_par import Par, ParRGB
from parrot.fixtures.motionstrip import Motionstrip
from parrot.fixtures.base import FixtureGroup, ManualGroup

from parrot.director.color_schemes import color_schemes
from parrot.director.color_scheme import ColorScheme

from parrot.interpreters.base import InterpreterArgs, InterpreterBase
from parrot.director.phrase import Phrase
from parrot.fixtures.laser import Laser
from parrot.fixtures.chauvet.rotosphere import ChauvetRotosphere_28Ch
from parrot.fixtures.chauvet.derby import ChauvetDerby
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

        self.state.set_phrase(Phrase.party)

        self.setup_patch()
        self.generate_color_scheme()
        self.phrase_machine = PhraseMachine(state)

        self.warmup_complete = False

        # Register event handlers
        self.state.events.on_phrase_change += self.on_phrase_change
        self.state.events.on_theme_change += lambda s: self.generate_color_scheme()
        self.state.events.on_venue_change += lambda s: self.setup_patch()

    def setup_patch(self):
        self.group_fixtures()
        self.generate_interpreters()

    def group_fixtures(self):
        to_group = [
            Par,
            MovingHead,
            Motionstrip,
            Laser,
            ChauvetRotosphere_28Ch,
            ChauvetDerby,
        ]
        self.fixture_groups = []

        # Get all fixtures from the venue patch
        all_fixtures = venue_patches[self.state.venue]

        # First, collect any existing FixtureGroup instances
        grouped_fixtures = []
        ungrouped_fixtures = []

        for fixture in all_fixtures:
            if isinstance(fixture, FixtureGroup):
                # Skip manual groups - they should not be controlled by interpreters
                if isinstance(fixture, ManualGroup):
                    continue
                self.fixture_groups.append(fixture.fixtures)
                grouped_fixtures.extend(fixture.fixtures)
            else:
                ungrouped_fixtures.append(fixture)

        # Then apply the existing algorithm to ungrouped fixtures
        for cls in to_group:
            fixtures = [i for i in ungrouped_fixtures if isinstance(i, cls)]
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
                    0 if not self.state.hype_limiter else max(0, self.state.hype - 30),
                    (
                        100
                        if not self.state.hype_limiter
                        else min(100, self.state.hype + 30)
                    ),
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
        print(f"Shifting to {ColorScheme.from_list(ct)}")

    def shift_interpreter(self):
        eviction_index = random.randint(0, len(self.interpreters) - 1)
        eviction_group = self.fixture_groups[eviction_index]

        hype_bracket = (
            0 if not self.state.hype_limiter else max(0, self.state.hype - 30),
            100 if not self.state.hype_limiter else min(100, self.state.hype + 30),
        )

        self.interpreters[eviction_index] = get_interpreter(
            self.state.phrase,
            eviction_group,
            InterpreterArgs(
                self.state.hype,
                self.state.theme.allow_rainbows,
                hype_bracket[0],
                hype_bracket[1],
            ),
        )

        print(
            f"Shifted interpretation for {self.state.phrase} hype=[{hype_bracket[0]} {hype_bracket[1]}]:"
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
        self.last_frame = frame
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
        # Get manual group and set its dimmer value
        manual_group = get_manual_group(self.state.venue)
        if manual_group:
            manual_group.set_manual_dimmer(self.state.manual_dimmer)

        # Render all fixtures
        for i in venue_patches[self.state.venue]:
            i.render(dmx)

        dmx.submit()

    def deploy_hype(self):
        self.phrase_machine.deploy_hype(self.last_frame)

    def on_phrase_change(self, phrase):
        """Handle phrase changes, including those from the web interface."""
        print(f"Phrase changed to: {phrase.name}")
        # Regenerate interpreters if needed
        self.generate_interpreters()
