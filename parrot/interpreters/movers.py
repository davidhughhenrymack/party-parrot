import random
from parrot.interpreters.base import (
    ColorFg,
    FlashBeat,
    InterpreterArgs,
    InterpreterBase,
    MoveCircles,
)
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


class MoverNoGobo(InterpreterBase[MovingHead]):

    def __init__(
        self,
        group,
        args: InterpreterArgs,
    ):
        super().__init__(group, args)

        for fixture in self.group:
            fixture.set_gobo("open")


MoverBeatAndCircle = combo(FlashBeat, MoveCircles, ColorFg)
MoverBeatInFan = combo(FlashBeat, MoverFan, ColorFg)
MoverSequenceAndCircle = combo(MoveCircles, ColorFg, SequenceDimmers)
MoverSequenceInFan = combo(SequenceDimmers, MoverFan, ColorFg)
MoverDimAndCircle = combo(MoveCircles, ColorFg, Dimmer30)
MoverOnAndCircle = combo(MoveCircles, ColorFg, Dimmer255)
