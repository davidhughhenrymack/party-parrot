from beartype import beartype
from parrot.director.color_scheme import ColorScheme
from parrot.interpreters.base import InterpreterBase
from parrot.director.frame import Frame
from parrot.fixtures.moving_head import MovingHead


@beartype
class StrobeHighSustained(InterpreterBase[MovingHead]):
    hype = 90

    def step(self, frame, scheme):
        for i in self.group:
            i.set_strobe(220)
            i.set_dimmer(255)

    def exit(self, frame: Frame, scheme: ColorScheme):
        for i in self.group:
            i.set_strobe(0)
            i.set_dimmer(0)
