from parrot.interpreters.base import (
    ColorFg,
    FlashBeat,
    InterpreterBase,
    MoveCircles,
)
from parrot.interpreters.dimmer import Dimmer100, Dimmer30, SequenceDimmers
from parrot.interpreters.combo import comboify
from parrot.fixtures.moving_head import MovingHead


class MoverFan(InterpreterBase[MovingHead]):
    def __init__(self, group):
        super().__init__(group)

        for i, fixture in enumerate(group):
            fixture.set_pan(i * 255 / len(group))
            fixture.set_tilt(128)

    def step(self, frame, scheme):
        pass


MoverBeatAndCircle = comboify([FlashBeat, MoveCircles, ColorFg])
MoverBeatInFan = comboify([FlashBeat, MoverFan, ColorFg])
MoverSequenceAndCircle = comboify([MoveCircles, ColorFg, SequenceDimmers])
MoverSequenceInFan = comboify([SequenceDimmers, MoverFan, ColorFg])
MoverDimAndCircle = comboify([MoveCircles, ColorFg, Dimmer30])
MoverOnAndCircle = comboify([MoveCircles, ColorFg, Dimmer100])
