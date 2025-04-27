import random
from typing import Dict, List, Type, TypeVar

from parrot.director.color_scheme import ColorScheme
from parrot.director.frame import Frame, FrameSignal
from parrot.fixtures.base import FixtureBase, FixtureWithBulbs
from parrot.interpreters.base import InterpreterArgs, InterpreterBase
from parrot.interpreters.bulbs import for_bulbs
from parrot.interpreters.dimmer import Twinkle

T = TypeVar("T", bound=FixtureBase)

# Probability constants for each signal
SIGNAL_PROBABILITIES = {
    FrameSignal.strobe: 0.4,
    FrameSignal.big_pulse: 0.7,
    FrameSignal.small_pulse: 0.3,
    FrameSignal.twinkle: 0.6,
    FrameSignal.dampen: 0.9,
}

# Decay rates for pulses
BIG_PULSE_DECAY = 0.9
SMALL_PULSE_DECAY = 0.8


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
            self.args = args  # Store args for use in twinkle interpreter

            # Randomly decide which signals to respond to
            self.responds_to = {
                signal: random.random() < probability
                for signal, probability in SIGNAL_PROBABILITIES.items()
            }

            # Initialize state
            self.big_pulse_dimmer = 0.0
            self.small_pulse_dimmer = 0.0
            self.twinkle_interp = None
            self.twinkle_active = False

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
                else:
                    for fixture in self.group:
                        fixture.set_strobe(0)
                        # Don't reset dimmer here as it might be controlled by other signals

            # Handle big pulse
            if self.responds_to.get(FrameSignal.big_pulse, False):
                if frame[FrameSignal.big_pulse] > 0.5:
                    self.big_pulse_dimmer = 225
                else:
                    self.big_pulse_dimmer = self.big_pulse_dimmer * BIG_PULSE_DECAY

            # Handle small pulse
            if self.responds_to.get(FrameSignal.small_pulse, False):
                if frame[FrameSignal.small_pulse] > 0.5:
                    self.small_pulse_dimmer = 225
                else:
                    self.small_pulse_dimmer = (
                        self.small_pulse_dimmer * SMALL_PULSE_DECAY
                    )

            # Handle dampen signal
            if (
                self.responds_to.get(FrameSignal.dampen, False)
                and frame[FrameSignal.dampen] > 0.5
            ):
                for fixture in self.group:
                    fixture.set_dimmer(0)  # Force dimmer to 0 when dampen is high
                return  # Skip further dimmer processing when dampen is active

            # Set dimmer to the maximum of the pulse values and standard interpreter's dimmer
            for fixture in self.group:
                current_dimmer = max(
                    self.big_pulse_dimmer,
                    self.small_pulse_dimmer,
                    fixture.get_dimmer(),
                )
                fixture.set_dimmer(current_dimmer)

            # Handle twinkle
            if self.responds_to.get(FrameSignal.twinkle, False):
                if frame[FrameSignal.twinkle] > 0.5:
                    if not self.twinkle_active:
                        self.twinkle_active = True
                        # Create twinkle interpreter for bulbs
                        bulb_fixtures = [
                            f for f in self.group if isinstance(f, FixtureWithBulbs)
                        ]
                        if bulb_fixtures:
                            self.twinkle_interp = for_bulbs(Twinkle)(
                                self.group, self.args
                            )
                        else:
                            self.twinkle_interp = Twinkle(self.group, self.args)
                else:
                    if self.twinkle_active:
                        self.twinkle_active = False
                        if self.twinkle_interp:
                            self.twinkle_interp.exit(frame, scheme)
                            self.twinkle_interp = None

                if self.twinkle_active and self.twinkle_interp:
                    self.twinkle_interp.step(frame, scheme)

        def exit(self, frame: Frame, scheme: ColorScheme):
            self.interp_std.exit(frame, scheme)
            for fixture in self.group:
                fixture.set_strobe(0)

            if self.twinkle_interp:
                self.twinkle_interp.exit(frame, scheme)

        def __str__(self) -> str:
            return str(self.interp_std)

    return SignalSwitch
