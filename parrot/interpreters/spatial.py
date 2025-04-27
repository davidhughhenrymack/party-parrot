import math
from typing import List, TypeVar
from parrot.director.frame import FrameSignal
from parrot.fixtures.base import FixtureBase
from parrot.interpreters.base import InterpreterArgs, InterpreterBase, with_args
from parrot.utils.math import clamp


T = TypeVar("T", bound=FixtureBase)


class SpatialDownwardsPulse(InterpreterBase[T]):
    hype = 60

    def __init__(
        self,
        group: List[T],
        args: InterpreterArgs,
        signal=FrameSignal.freq_high,
        trigger_level=0.3,
        edge_hardness=2.0,
        pulse_width=0.3,
        speed=1.0,
    ):
        super().__init__(group, args)
        self.signal = signal
        self.trigger_level = trigger_level
        self.edge_hardness = edge_hardness
        self.pulse_width = pulse_width
        self.speed = speed

        # Initialize state
        self.pulse_position = 0
        self.active = False
        self.valid_fixtures = []
        self.y_start = 0
        self.y_end = 0
        self.y_range = 0

    def _calculate_spatial_range(self):
        # Filter fixtures with valid y positions
        self.valid_fixtures = [
            f for f in self.group if hasattr(f, "y") and f.y is not None
        ]

        if not self.valid_fixtures:
            return False

        # Calculate the spatial range with 30% margin
        y_positions = [fixture.y for fixture in self.valid_fixtures]
        min_y = min(y_positions)
        max_y = max(y_positions)
        y_range = max_y - min_y

        self.y_start = min_y - (y_range * 0.3)
        self.y_end = max_y + (y_range * 0.3)
        self.y_range = self.y_end - self.y_start

        return True

    def step(self, frame, scheme):
        # Check if we should start a new pulse
        if frame[self.signal] > self.trigger_level and not self.active:
            # Recalculate spatial range when starting a new pulse
            if not self._calculate_spatial_range():
                # If no valid fixtures, just turn everything off
                for fixture in self.group:
                    fixture.set_dimmer(0)
                return

            self.active = True
            self.pulse_position = self.y_start

        if self.active:
            # Move the pulse downward
            self.pulse_position += self.speed * (self.y_range / 30)  # Assuming 30 FPS

            # Check if pulse has reached the end
            if self.pulse_position > self.y_end:
                self.active = False
                return

            # Calculate intensity for each fixture based on its y position
            for fixture in self.valid_fixtures:
                # Calculate normalized distance from pulse center
                distance = abs(fixture.y - self.pulse_position) / (self.y_range + 1e-6)

                # Calculate intensity using a smooth falloff
                # The pulse_width controls how wide the pulse is
                # The edge_hardness controls how sharp the edges are
                normalized_distance = distance / self.pulse_width
                intensity = max(0, 1 - (normalized_distance**self.edge_hardness))

                # Set the dimmer value
                fixture.set_dimmer(int(intensity * 255))

            # Turn off any fixtures without valid y positions
            for fixture in self.group:
                if fixture not in self.valid_fixtures:
                    fixture.set_dimmer(0)
        else:
            # Turn off all fixtures when not active
            for fixture in self.group:
                fixture.set_dimmer(0)


# Fast, hard-edged version
HardSpatialPulse = with_args(
    "HardSpatialPulse",
    SpatialDownwardsPulse,
    new_hype=90,
    edge_hardness=4.0,
    pulse_width=0.2,
    speed=2.0,
)

# Slow, soft-edged version
SoftSpatialPulse = with_args(
    "SoftSpatialPulse",
    SpatialDownwardsPulse,
    new_hype=30,
    edge_hardness=1.5,
    pulse_width=0.4,
    speed=0.5,
)
