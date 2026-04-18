import random
from parrot.interpreters.base import (
    ColorFg,
    FlashBeat,
    InterpreterArgs,
    InterpreterBase,
)
from parrot.interpreters.move import MoveCircles
from parrot.interpreters.dimmer import Dimmer255, Dimmer30, SequenceDimmers
from parrot.interpreters.combo import combo
from parrot.fixtures.moving_head import MovingHead
from parrot.utils.colour import Color


class MoverFan(InterpreterBase[MovingHead]):

    def __init__(
        self,
        group,
        args: InterpreterArgs,
    ):
        super().__init__(group, args)

        for i, fixture in enumerate(group):
            fixture.set_pan(i * 255 / len(group))
            fixture.set_tilt(128)

    def step(self, frame, scheme):
        pass


class MoverRandomGobo(InterpreterBase[MovingHead]):

    def __init__(
        self,
        group,
        args: InterpreterArgs,
    ):
        super().__init__(group, args)

        for fixture in self.group:
            fixture.set_gobo(random.choice(fixture.gobo_wheel).name)


class MoverGobo(InterpreterBase[MovingHead]):

    def __init__(self, group, args: InterpreterArgs, gobo: str):
        super().__init__(group, args)

        for fixture in self.group:
            fixture.set_gobo(gobo)


class MoverNoGobo(InterpreterBase[MovingHead]):

    def __init__(
        self,
        group,
        args: InterpreterArgs,
    ):
        super().__init__(group, args)

        for fixture in self.group:
            fixture.set_gobo("open")


class FocusBig(InterpreterBase[MovingHead]):
    """Pin focus wide-open (big/unfocused beam) on every fixture in the group.

    MovingHead fixtures without a focus channel accept the call; the write is
    a no-op for subclasses whose ``dmx_layout`` lacks a "focus" entry.
    """

    def __init__(self, group, args: InterpreterArgs):
        super().__init__(group, args)
        for fixture in self.group:
            fixture.set_focus(0.0)

    def step(self, frame, scheme):
        for fixture in self.group:
            fixture.set_focus(0.0)


class FocusSmall(InterpreterBase[MovingHead]):
    """Pin focus fully tight (small/sharp beam) on every fixture in the group.

    Mirror of :class:`FocusBig`. Fixtures lacking a focus channel accept the
    call; the DMX write is a no-op for them.
    """

    def __init__(self, group, args: InterpreterArgs):
        super().__init__(group, args)
        for fixture in self.group:
            fixture.set_focus(1.0)

    def step(self, frame, scheme):
        for fixture in self.group:
            fixture.set_focus(1.0)


class RotatingGobo(InterpreterBase[MovingHead]):
    """Select a rotating-gobo-wheel slot and keep it spinning.

    ``slot`` is 1-indexed per the Chauvet Intimidator Hybrid 140SR rotating
    gobo wheel (1–8 → gobos 1–8, 0 → open/beam). ``rotate_speed`` is in
    [-1, 1]; ``0`` leaves the gobo static (indexed), ``+1`` is fastest forward,
    ``-1`` is fastest reverse. MovingHead fixtures without a rotating gobo
    channel accept the call; it just has no DMX effect for those subclasses.
    """

    def __init__(
        self,
        group,
        args: InterpreterArgs,
        slot: int,
        rotate_speed: float = 0.3,
    ):
        super().__init__(group, args)
        self._slot = slot
        self._rotate_speed = rotate_speed
        for fixture in self.group:
            fixture.set_rotating_gobo(slot, rotate_speed)

    def step(self, frame, scheme):
        # Re-assert each frame so other interpreters can't drift the wheel off.
        for fixture in self.group:
            fixture.set_rotating_gobo(self._slot, self._rotate_speed)

    def exit(self, frame, scheme):
        for fixture in self.group:
            fixture.set_rotating_gobo(0, 0.0)


class RotatePrism(InterpreterBase[MovingHead]):
    """Turn the prism on and spin it at a constant rate.

    ``rotate_speed`` is in [-1, 1]; 0 = static prism on (no rotation).
    MovingHead fixtures without a prism still accept the call; it just has no
    DMX effect for those subclasses.
    """

    def __init__(
        self,
        group,
        args: InterpreterArgs,
        rotate_speed: float = 0.25,
    ):
        super().__init__(group, args)
        self._rotate_speed = rotate_speed
        for fixture in self.group:
            fixture.set_prism(True, rotate_speed)

    def step(self, frame, scheme):
        # Keep the prism asserted each frame in case another interpreter toggled it.
        for fixture in self.group:
            fixture.set_prism(True, self._rotate_speed)

    def exit(self, frame, scheme):
        for fixture in self.group:
            fixture.set_prism(False, 0.0)


class PrismOff(InterpreterBase[MovingHead]):
    """Explicitly disable the prism on a group each frame."""

    def __init__(self, group, args: InterpreterArgs):
        super().__init__(group, args)
        for fixture in self.group:
            fixture.set_prism(False, 0.0)

    def step(self, frame, scheme):
        for fixture in self.group:
            fixture.set_prism(False, 0.0)


MoverBeatAndCircle = combo(FlashBeat, MoveCircles, ColorFg)
MoverBeatInFan = combo(FlashBeat, MoverFan, ColorFg)
MoverSequenceAndCircle = combo(MoveCircles, ColorFg, SequenceDimmers)
MoverSequenceInFan = combo(SequenceDimmers, MoverFan, ColorFg)
MoverDimAndCircle = combo(MoveCircles, ColorFg, Dimmer30)
MoverOnAndCircle = combo(MoveCircles, ColorFg, Dimmer255)
