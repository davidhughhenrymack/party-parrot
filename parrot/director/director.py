import random
import time
import os
from typing import List, Dict
from parrot.director.frame import Frame, FrameSignal
from parrot.director.mode_machine import ModeMachine
from parrot.fixtures import laser

from parrot.patch_bay import venue_patches, get_manual_group, venues
from parrot.fixtures.led_par import Par, ParRGB
from parrot.fixtures.motionstrip import Motionstrip
from parrot.fixtures.base import FixtureGroup, ManualGroup, FixtureBase

from parrot.director.color_schemes import color_schemes
from parrot.director.color_scheme import ColorScheme

from parrot.interpreters.base import InterpreterArgs, InterpreterBase
from parrot.director.mode import Mode
from parrot.fixtures.laser import Laser
from parrot.fixtures.chauvet.rotosphere import ChauvetRotosphere_28Ch
from parrot.fixtures.chauvet.derby import ChauvetDerby
from .mode_interpretations import get_interpreter
from parrot.director.scenes import get_scene_interpreter

from parrot.utils.lerp import LerpAnimator
from parrot.fixtures.moving_head import MovingHead
from parrot.state import State
import numpy as np

SHIFT_AFTER = 60
WARMUP_SECONDS = max(int(os.environ.get("WARMUP_TIME", "1")), 1)

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
        self.last_frame = None
        self.mode_machine = None
        self.scene_values = {}  # Track scene slider values
        self.interpreters = {}  # Cache of interpreters for each mode/scene

        self.state.set_mode(Mode.party)

        self.setup_patch()
        self.generate_color_scheme()
        self.mode_machine = ModeMachine(state)

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

    def generate_interpreters(self):
        """Generate interpreters for the current mode and scenes."""
        self.interpreters = {}

        # Generate mode interpreters
        mode = self.state.mode
        for fixture_group in venue_patches[self.state.venue]:
            if isinstance(fixture_group, list):
                interpreter = get_interpreter(mode, fixture_group, InterpreterArgs())
                if interpreter:
                    self.interpreters[(mode, fixture_group[0].address)] = interpreter

        # Generate scene interpreters
        for scene_name in self.scene_values:
            for fixture_group in venue_patches[self.state.venue]:
                if isinstance(fixture_group, list):
                    interpreter = get_scene_interpreter(
                        scene_name, fixture_group, InterpreterArgs()
                    )
                    if interpreter:
                        self.interpreters[(scene_name, fixture_group[0].address)] = (
                            interpreter
                        )

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
            self.state.mode,
            eviction_group,
            InterpreterArgs(
                self.state.hype,
                self.state.theme.allow_rainbows,
                hype_bracket[0],
                hype_bracket[1],
            ),
        )

        print(
            f"Shifted interpretation for {self.state.mode} hype=[{hype_bracket[0]} {hype_bracket[1]}]:"
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

        additional_signals = self.mode_machine.step(frame)
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
        """Render all fixtures with highest-takes-precedence logic."""
        # Create a temporary DMX buffer to store all values
        temp_dmx = np.zeros(512, dtype=np.uint8)

        # Render all interpreters
        for (source, address), interpreter in self.interpreters.items():
            # Get the multiplier for this source
            if isinstance(source, Mode):
                multiplier = 1.0  # Mode always runs at full strength
            else:
                multiplier = self.scene_values.get(source, 0.0)

            if multiplier > 0:
                # Create a temporary fixture to capture the values
                temp_fixture = interpreter.group[0]
                interpreter.step(self.last_frame, None)

                # Apply the values to the temporary DMX buffer
                for i in range(temp_fixture.width):
                    channel = temp_fixture.address + i - 1  # Convert to 0-based
                    if channel >= 0 and channel < 512:
                        # Take the highest value
                        temp_dmx[channel] = max(
                            temp_dmx[channel], int(temp_fixture.values[i] * multiplier)
                        )

        # Copy the final values to the real DMX buffer
        for i in range(512):
            if temp_dmx[i] > 0:
                dmx.set_channel(i + 1, temp_dmx[i])  # Convert back to 1-based

        dmx.submit()

    def deploy_hype(self):
        self.mode_machine.deploy_hype(self.last_frame)

    def on_mode_change(self, mode):
        """Handle mode changes, including those from the web interface."""
        print(f"mode changed to: {mode.name}")
        # Regenerate interpreters if needed
        self.generate_interpreters()

    def set_scene_value(self, scene_name: str, value: float):
        """Set the value for a scene (0-1)."""
        self.scene_values[scene_name] = value
        self.generate_interpreters()
