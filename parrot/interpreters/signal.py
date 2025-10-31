import random
from typing import Dict, List, Type, TypeVar

from parrot.director.color_scheme import ColorScheme
from parrot.director.frame import Frame, FrameSignal
from parrot.fixtures.base import FixtureBase, FixtureWithBulbs
from parrot.interpreters.base import InterpreterArgs, InterpreterBase
from parrot.interpreters.bulbs import for_bulbs
from parrot.interpreters.spatial import HardSpatialCenterOutPulse, HardSpatialPulse


T = TypeVar("T", bound=FixtureBase)

# Probability constants for each signal
SIGNAL_PROBABILITIES = {
    FrameSignal.strobe: 0.4,
    FrameSignal.big_blinder: 0.7,
    FrameSignal.small_blinder: 0.3,
    FrameSignal.pulse: 0.9,
    FrameSignal.dampen: 0.9,
}

# Decay rates for pulses
BIG_BLINDER_DECAY = 0.9
SMALL_BLINDER_DECAY = 0.8


def signal_switch(
    interp_std: Type[InterpreterBase[T]],
) -> Type[InterpreterBase[T]]:

    class SignalSwitch(InterpreterBase[T]):
        def __init__(
            self,
            group: List[T],
            args: InterpreterArgs,
        ):
            super().__init__(group, args)

            self.interp_std = interp_std(group, args)
            self.args = args  # Store args for use in pulse interpreter

            # Randomly decide which signals to respond to
            self.responds_to = {
                signal: random.random() < probability
                for signal, probability in SIGNAL_PROBABILITIES.items()
            }

            self.pulse_type = random.choice(
                [HardSpatialPulse, HardSpatialCenterOutPulse]
            )

            # Initialize state
            self.big_blinder_dimmer = 0.0
            self.small_blinder_dimmer = 0.0
            self.pulse_interp = None
            self.pulse_active = False

        def is_enabled(self, signal: FrameSignal) -> bool:
            return self.responds_to.get(signal, False)

        def set_enabled(self, signal: FrameSignal, enabled: bool):
            if signal in self.responds_to:
                self.responds_to[signal] = enabled

        def step(self, frame: Frame, scheme: ColorScheme):
            # Always run standard interpreter first
            self.interp_std.step(frame, scheme)

            # Handle strobe signal
            if self.responds_to.get(FrameSignal.strobe, False):
                if frame[FrameSignal.strobe] > 0.5:
                    for fixture in self.group:
                        fixture.set_strobe(220)
                        fixture.set_dimmer(225)  # Set dimmer high during strobe
                        if isinstance(fixture, FixtureWithBulbs):
                            for bulb in fixture.get_bulbs():
                                bulb.set_strobe(220)
                                bulb.set_dimmer(225)

                else:
                    for fixture in self.group:
                        fixture.set_strobe(0)
                        # Don't reset dimmer here as it might be controlled by other signals

            # Handle big blinder
            if self.responds_to.get(FrameSignal.big_blinder, False):
                if frame[FrameSignal.big_blinder] > 0.5:
                    self.big_blinder_dimmer = 225
                else:
                    self.big_blinder_dimmer = (
                        self.big_blinder_dimmer * BIG_BLINDER_DECAY
                    )

            # Handle small blinder
            if self.responds_to.get(FrameSignal.small_blinder, False):
                if frame[FrameSignal.small_blinder] > 0.5:
                    self.small_blinder_dimmer = 225
                else:
                    self.small_blinder_dimmer = (
                        self.small_blinder_dimmer * SMALL_BLINDER_DECAY
                    )

            # Handle dampen signal
            if (
                self.responds_to.get(FrameSignal.dampen, False)
                and frame[FrameSignal.dampen] > 0.5
            ):
                for fixture in self.group:
                    fixture.set_dimmer(0)  # Force dimmer to 0 when dampen is high
                return  # Skip further dimmer processing when dampen is active

            # Set dimmer to the maximum of the blinder values and standard interpreter's dimmer
            for fixture in self.group:
                current_dimmer = max(
                    self.big_blinder_dimmer,
                    self.small_blinder_dimmer,
                    fixture.get_dimmer(),
                )
                fixture.set_dimmer(current_dimmer)

            # Handle pulse
            if self.responds_to.get(FrameSignal.pulse, False):
                if frame[FrameSignal.pulse] > 0.5:
                    if not self.pulse_active:
                        self.pulse_active = True
                        # Create pulse interpreter for bulbs
                        bulb_fixtures = [
                            f for f in self.group if isinstance(f, FixtureWithBulbs)
                        ]
                        if bulb_fixtures:
                            self.pulse_interp = for_bulbs(self.pulse_type)(
                                self.group, self.args
                            )
                        else:
                            self.pulse_interp = self.pulse_type(self.group, self.args)
                else:
                    if self.pulse_active:
                        self.pulse_active = False
                        if self.pulse_interp:
                            self.pulse_interp.exit(frame, scheme)
                            self.pulse_interp = None

                if self.pulse_active and self.pulse_interp:
                    self.pulse_interp.step(frame, scheme)

        def exit(self, frame: Frame, scheme: ColorScheme):
            self.interp_std.exit(frame, scheme)
            for fixture in self.group:
                fixture.set_strobe(0)

            if self.pulse_interp:
                self.pulse_interp.exit(frame, scheme)

        def __str__(self) -> str:
            return str(self.interp_std)

    return SignalSwitch
