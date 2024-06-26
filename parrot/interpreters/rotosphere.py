from typing import List
from parrot.fixtures.chauvet.rotosphere import ChauvetRotosphere_28Ch
from parrot.interpreters.base import ColorAlternateBg, InterpreterArgs, InterpreterBase
from parrot.interpreters.combo import combo
from parrot.interpreters.latched import DimmerFadeLatched
from parrot.interpreters.dimmer import Dimmer255
from parrot.interpreters.bulbs import for_bulbs
from parrot.fixtures.base import FixtureBase


class Spin(InterpreterBase[FixtureBase]):

    def __init__(self, group: List[FixtureBase], args: InterpreterArgs, speed=50):
        super().__init__(group, args)
        self.speed = speed

    def step(self, frame, scheme):
        for fixture in self.group:
            fixture.set_speed(self.speed)


RotosphereSpinColor = combo(Spin, for_bulbs(ColorAlternateBg))
RotosphereOn = combo(RotosphereSpinColor, Dimmer255)
