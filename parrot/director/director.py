import random
import re
import time
import os
from collections import defaultdict
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
from parrot.fixtures.position_manager import FixturePositionManager

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

        # Initialize position manager first (so fixtures have positions before interpreters are created)
        self.position_manager = FixturePositionManager(state)

        self.setup_patch()
        self.generate_color_scheme()

        self.warmup_complete = False

        # Register event handlers
        self.state.events.on_mode_change += self.on_mode_change
        self.state.events.on_theme_change += lambda s: self.generate_color_scheme()
        self.state.events.on_venue_change += lambda s: self.setup_patch()

    def setup_patch(self):
        self.group_fixtures()
        self.generate_all()  # Initialize both lighting and VJ

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
        if len(fixtures) == 1:
            return fixtures[0]
        
        # Group fixtures by type (base name)
        grouped = defaultdict(list)
        for f in fixtures:
            parts = f.split(" @ ")
            base_name = parts[0]
            address = int(parts[1])
            grouped[base_name].append(address)
        
        # Format each group: "type @ addr1, addr2, addr3"
        parts = []
        for base_name in sorted(grouped.keys()):
            addresses = sorted(grouped[base_name])
            addr_str = ", ".join(str(addr) for addr in addresses)
            parts.append(f"{base_name} @ {addr_str}")
        
        return "; ".join(parts)

    def print_lighting_tree(self, context: str = ""):
        """Print a tree representation of the lighting interpreters"""
        result = "DMX Lighting Tree"
        if context:
            result += f" ({context})"
        result += ":\n"
        
        if not hasattr(self, 'interpreters') or not self.interpreters:
            result += "└── (no interpreters)\n"
            return result
        
        result += "└── LightingInterpreters\n"
        
        for idx, interpreter in enumerate(self.interpreters):
            is_last = idx == len(self.interpreters) - 1
            connector = "└── " if is_last else "├── "
            indent = "    " if is_last else "│   "
            
            fixture_str = self.format_fixture_names(interpreter.group)
            # Strip all ANSI escape sequences from interpreter string
            interpreter_str = re.sub(r'\x1b\[[0-9;]*m', '', str(interpreter))
            
            result += f"{indent}{connector}{Fore.BLUE}{fixture_str}{Style.RESET_ALL} {interpreter_str}\n"
        
        return result

    def generate_interpreters(self):
        """Generate interpreters for lighting only (does not affect VJ)"""
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

        print(self.print_lighting_tree(f"after initialization to {self.state.mode.name}"))

    def generate_all(self):
        """Generate both lighting interpreters and VJ visuals"""
        self.generate_interpreters()

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

    def shift_lighting_only(self):
        """Full shift of DMX lighting only (no VJ changes) - regenerates all interpreters"""
        self.generate_color_scheme()

        # Regenerate all interpreters (similar to generate_interpreters but without VJ shift)
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

        self.ensure_each_signal_is_enabled()

        self.last_shift_time = time.time()
        self.shift_count += 1

        # Print the tree structure after shift
        print(self.print_lighting_tree(f"after shift #{self.shift_count} to {self.state.mode.name}"))

    def shift_vj_only(self):
        """Full shift of VJ visuals only (no lighting changes) - complete regeneration"""
        if self.vj_director:
            self.vj_director.shift(self.state.vj_mode, threshold=1.0)

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

        # Print the tree structure after shift
        print(self.print_lighting_tree(f"after shift #{self.shift_count} to {self.state.mode.name}"))

    def step(self, frame: Frame):
        self.last_frame = frame
        scheme = self.scheme.render()
        run_time = time.time() - self.start_time
        warmup_phase = min(1, run_time / WARMUP_SECONDS)

        if warmup_phase == 1 and not self.warmup_complete:
            print("Warmup phase complete")
            self.warmup_complete = True

        frame = frame * warmup_phase

        # Reset fixture state before interpreter step() calls
        # This ensures strobe values accumulate using max(existing, new)
        for fixture in venue_patches[self.state.venue]:
            fixture.begin()

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
            manual_group.render(dmx)

        # Render all fixtures
        for i in venue_patches[self.state.venue]:
            i.render(dmx)

        dmx.submit()

    def deploy_hype(self):
        self.mode_machine.deploy_hype(self.last_frame)

    def on_mode_change(self, mode):
        """Handle mode changes, including those from the web interface."""
        print(f"mode changed to: {mode.name}")
        # Regenerate lighting interpreters only (VJ is independent)
        self.generate_interpreters()
        print(self.print_lighting_tree(f"after mode change to {mode.name}"))
