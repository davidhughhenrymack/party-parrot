from parrot.interpreters.base import (
    ColorFg,
    Dimmer30,
    FlashBeat,
    GroupInterpreterBase,
    MoveCircles,
)
from parrot.interpreters.combo import comboify, group_comboify
from parrot.fixtures.moving_head import MovingHead
from parrot.interpreters.group import SequenceDimmers


class MoverFan(GroupInterpreterBase[MovingHead]):
    def __init__(self, group):
        super().__init__(group)

        for i, fixture in enumerate(group):
            fixture.set_pan(i * 255 / len(group))
            fixture.set_tilt(128)

    def step(self, frame, scheme):
        pass


MoverBeatAndCircle = comboify([FlashBeat, MoveCircles, ColorFg])
MoverGroupBeatInFan = group_comboify([FlashBeat, MoverFan, ColorFg])
MoverSequenceAndCircle = group_comboify([MoveCircles, ColorFg, SequenceDimmers])
MoverSequenceInFan = group_comboify([SequenceDimmers, MoverFan, ColorFg])
MoverDimAndCircle = group_comboify([MoveCircles, ColorFg, Dimmer30])
