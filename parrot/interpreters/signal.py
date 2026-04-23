import random
from typing import List, Type, TypeVar

from parrot.director.color_scheme import ColorScheme
from parrot.director.frame import Frame, FrameSignal
from parrot.fixtures.base import FixtureBase, FixtureWithBulbs
from parrot.interpreters.base import ColorRainbow, InterpreterArgs, InterpreterBase
from parrot.interpreters.bulbs import for_bulbs
from parrot.interpreters.dimmer import (
    Dimmer255,
    GentlePulse,
    SequenceFadeDimmers,
    SlowBreath,
    Twinkle,
)


T = TypeVar("T", bound=FixtureBase)

# Probability constants for each signal (% of fixtures that recruit for this carrier)
SIGNAL_PROBABILITIES = {
    FrameSignal.strobe: 0.4,
    FrameSignal.big_blinder: 0.7,
    FrameSignal.rainbow: 0.95,
    FrameSignal.chase: 0.95,
}

BIG_BLINDER_DECAY = 0.9


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
            self.args = args

            self.responds_to = {
                signal: random.random() < probability
                for signal, probability in SIGNAL_PROBABILITIES.items()
            }

            self.big_blinder_dimmer = 0.0

            self.chase_active = False
            self.chase_interp = None

            self.rainbow_active = False
            self.rainbow_color_interp = None
            self.rainbow_twinkle_interp = None

        def is_enabled(self, signal: FrameSignal) -> bool:
            return self.responds_to.get(signal, False)

        def set_enabled(self, signal: FrameSignal, enabled: bool):
            if signal in self.responds_to:
                self.responds_to[signal] = enabled

        def _make_chase_interp(self):
            bulb_fixtures = [f for f in self.group if isinstance(f, FixtureWithBulbs)]
            if bulb_fixtures:
                return for_bulbs(SequenceFadeDimmers)(self.group, self.args)
            return SequenceFadeDimmers(self.group, self.args)

        def _make_rainbow_interps(self):
            bulb_fixtures = [f for f in self.group if isinstance(f, FixtureWithBulbs)]
            if bulb_fixtures:
                return (
                    for_bulbs(ColorRainbow)(self.group, self.args),
                    for_bulbs(GentlePulse)(self.group, self.args),
                )
            return (
                ColorRainbow(self.group, self.args),
                GentlePulse(self.group, self.args),
            )

        def step(self, frame: Frame, scheme: ColorScheme):
            self.interp_std.step(frame, scheme)

            if self.responds_to.get(FrameSignal.strobe, False):
                if frame[FrameSignal.strobe] > 0.5:
                    for fixture in self.group:
                        fixture.set_strobe(220)
                        fixture.set_dimmer(225)
                        if isinstance(fixture, FixtureWithBulbs):
                            for bulb in fixture.get_bulbs():
                                bulb.set_strobe(220)
                                bulb.set_dimmer(225)

                else:
                    for fixture in self.group:
                        fixture.set_strobe(0)

            if self.responds_to.get(FrameSignal.big_blinder, False):
                if frame[FrameSignal.big_blinder] > 0.5:
                    self.big_blinder_dimmer = 225
                else:
                    self.big_blinder_dimmer = (
                        self.big_blinder_dimmer * BIG_BLINDER_DECAY
                    )

            for fixture in self.group:
                current_dimmer = max(
                    self.big_blinder_dimmer,
                    fixture.get_dimmer(),
                )
                fixture.set_dimmer(current_dimmer)

            if self.responds_to.get(FrameSignal.rainbow, False):
                if frame[FrameSignal.rainbow] > 0.5:
                    if not self.rainbow_active:
                        self.rainbow_active = True
                        (
                            self.rainbow_color_interp,
                            self.rainbow_twinkle_interp,
                        ) = self._make_rainbow_interps()
                else:
                    if self.rainbow_active:
                        self.rainbow_active = False
                        if self.rainbow_color_interp:
                            self.rainbow_color_interp.exit(frame, scheme)
                            self.rainbow_color_interp = None
                        if self.rainbow_twinkle_interp:
                            self.rainbow_twinkle_interp.exit(frame, scheme)
                            self.rainbow_twinkle_interp = None

                if (
                    self.rainbow_active
                    and self.rainbow_color_interp
                    and self.rainbow_twinkle_interp
                ):
                    self.rainbow_color_interp.step(frame, scheme)
                    self.rainbow_twinkle_interp.step(frame, scheme)

            if self.responds_to.get(FrameSignal.chase, False):
                if frame[FrameSignal.chase] > 0.5:
                    if not self.chase_active:
                        self.chase_active = True
                        self.chase_interp = self._make_chase_interp()
                else:
                    if self.chase_active:
                        self.chase_active = False
                        if self.chase_interp:
                            self.chase_interp.exit(frame, scheme)
                            self.chase_interp = None

                if self.chase_active and self.chase_interp:
                    self.chase_interp.step(frame, scheme)

        def exit(self, frame: Frame, scheme: ColorScheme):
            self.interp_std.exit(frame, scheme)
            for fixture in self.group:
                fixture.set_strobe(0)

            if self.chase_interp:
                self.chase_interp.exit(frame, scheme)
            if self.rainbow_color_interp:
                self.rainbow_color_interp.exit(frame, scheme)
            if self.rainbow_twinkle_interp:
                self.rainbow_twinkle_interp.exit(frame, scheme)

        def __str__(self):
            return str(self.interp_std)

    return SignalSwitch
