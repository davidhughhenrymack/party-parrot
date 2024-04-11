from typing import List
from parrot.fixtures.chauvet.rotosphere import ChauvetRotosphere_28Ch
from parrot.interpreters.base import InterpreterBase
from parrot.interpreters.combo import combo
from parrot.interpreters.latched import DimmerFadeLatched
from parrot.interpreters.dimmer import Dimmer100


class RotosphereColor(InterpreterBase[ChauvetRotosphere_28Ch]):

    def __init__(self, group: List[ChauvetRotosphere_28Ch]):
        super().__init__(group)

    def step(self, frame, scheme):
        for fixture in self.group:
            fixture.set_speed(50)
            for i, bulb in enumerate(fixture.get_bulbs()):
                bulb.set_color(scheme.bg if i % 2 == 0 else scheme.bg_contrast)


RotosphereAll = combo(
    RotosphereColor,
    lambda group: DimmerFadeLatched(
        group,
        condition_on=lambda x: x < 0.1,
        condition_off=lambda x: x > 0.4,
        latch_time=10,
    ),
)

RotosphereOn = combo(RotosphereColor, Dimmer100)
