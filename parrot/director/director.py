import random
import time
import os
from typing import List
from colorama import Fore, Style, init
from parrot.director.frame import Frame, FrameSignal

from parrot.patch_bay import venue_patches, get_manual_group
from parrot.fixtures.led_par import Par
from parrot.fixtures.motionstrip import Motionstrip
from parrot.fixtures.base import FixtureGroup, ManualGroup

from parrot.director.color_schemes import color_schemes
from parrot.director.color_scheme import ColorScheme

from parrot.interpreters.base import InterpreterArgs, InterpreterBase
from parrot.director.mode import Mode
from parrot.fixtures.laser import Laser
from parrot.fixtures.chauvet.rotosphere import ChauvetRotosphere_28Ch
from parrot.fixtures.chauvet.derby import ChauvetDerby
from .mode_interpretations import get_interpreter

from parrot.utils.lerp import LerpAnimator
from parrot.fixtures.moving_head import MovingHead
from parrot.state import State
from parrot.utils.color_utils import format_color_scheme

SHIFT_AFTER = 60
WARMUP_SECONDS = max(int(os.environ.get("WARMUP_TIME", "1")), 1)

HYPE_BUCKETS = [10, 40, 70]


def filter_nones(l):
    return [i for i in l if i is not None]


class Director:
    def __init__(self, state: State, vj_director=None):
        self.scheme = LerpAnimator(random.choice(color_schemes), 4)
        self.last_shift_time = time.time()
        self.shift_count = 0
        self.start_time = time.time()
        self.state = state
        self.vj_director = vj_director

        self.setup_patch()
        self.generate_color_scheme()

        self.warmup_complete = False

        # Register event handlers
        self.state.events.on_mode_change += self.on_mode_change
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

    def format_fixture_names(self, fixtures):
        # Format fixtures
        fixtures = [str(j) for j in fixtures]
        if len(fixtures) > 1:
            # Check if all fixtures have same name
            base_names = [f.split(" @ ")[0] for f in fixtures]
            if len(set(base_names)) == 1:
                # Get all addresses
                addresses = [int(f.split(" @ ")[1]) for f in fixtures]
                min_addr = min(addresses)
                max_addr = max(addresses)
                fixture_str = f"{base_names[0]} @ {min_addr}-{max_addr}"
            else:
                fixture_str = ", ".join(fixtures)
        else:
            fixture_str = fixtures[0]
        return fixture_str

    def generate_interpreters(self):
        self.interpreters: List[InterpreterBase] = [
            get_interpreter(
                self.state.mode,
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

        print(f"Generated interpretation for {self.state.mode}:")
        for i in self.interpreters:
            fixture_str = self.format_fixture_names(i.group)
            print(
                f"{Fore.BLUE}{fixture_str} {Style.RESET_ALL}{str(i)}{Style.RESET_ALL}"
            )

        print()

        # Also shift VJ director with high threshold for "shift all" (complete regeneration)
        if self.vj_director:
            self.vj_director.shift(self.state.vj_mode, threshold=1.0)

    def generate_color_scheme(self):
        s = random.choice(self.state.theme.color_scheme)
        self.scheme.push(s)
        print(f"Shifting to {format_color_scheme(s)}")

    def shift_color_scheme(self):
        s = random.choice(self.state.theme.color_scheme)
        st = s.to_list()
        ct = self.scheme.render().to_list()
        idx = random.randint(0, 2)
        ct[idx] = st[idx]
        new_scheme = ColorScheme.from_list(ct)
        self.scheme.push(new_scheme)
        print(f"Shifting to {format_color_scheme(new_scheme)}")

    def shift_interpreter(self):
        eviction_index = random.randint(0, len(self.interpreters) - 1)
        eviction_group = self.fixture_groups[eviction_index]

        hype_bracket = (
            0 if not self.state.hype_limiter else max(0, self.state.hype - 30),
            100 if not self.state.hype_limiter else min(100, self.state.hype + 30),
        )

        self.interpreters[eviction_index] = get_interpreter(
            self.state.mode,
            eviction_group,
            InterpreterArgs(
                self.state.hype,
                self.state.theme.allow_rainbows,
                hype_bracket[0],
                hype_bracket[1],
            ),
        )

        fixture_str = self.format_fixture_names(eviction_group)
        print(f"Shifted interpretation for {self.state.mode}:{Style.RESET_ALL}")
        print(
            f"{Fore.BLUE}{fixture_str}{Style.RESET_ALL} {str(self.interpreters[eviction_index])}{Style.RESET_ALL}"
        )

    def ensure_each_signal_is_enabled(self):
        """Makes a list of every interpreter that is a SignalSwitch. Then for each signal they handle, ensures
        at least one interpreter handles it. If not, a randomly selected SignalSwitch has the un-handled signal enabled.
        """
        signal_switches = [
            i
            for i in self.interpreters
            if hasattr(i, "responds_to") and hasattr(i, "set_enabled")
        ]
        if not signal_switches:
            return

        for signal in FrameSignal:
            if not any(i.responds_to.get(signal, False) for i in signal_switches):
                random.choice(signal_switches).set_enabled(signal, True)

    def shift(self):
        """Shift DMX lighting and VJ together"""
        self.shift_color_scheme()
        self.shift_interpreter()
        self.ensure_each_signal_is_enabled()

        # Shift VJ director if available (with moderate threshold for subtle changes)
        if self.vj_director:
            self.vj_director.shift(self.state.vj_mode, threshold=0.3)

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

        for i in self.interpreters:
            i.step(frame, scheme)

        # Pass frame and scheme to VJ system for rendering
        if self.vj_director:
            self.vj_director.step(frame, scheme)

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
        self.mode_machine.deploy_hype(self.last_frame)

    def on_mode_change(self, mode):
        """Handle mode changes, including those from the web interface."""
        print(f"mode changed to: {mode.name}")
        # Regenerate interpreters if needed (this also handles VJ shifts)
        self.generate_interpreters()
