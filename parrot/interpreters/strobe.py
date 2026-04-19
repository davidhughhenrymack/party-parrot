from beartype import beartype
from parrot.director.color_scheme import ColorScheme
from parrot.director.frame import Frame
from parrot.fixtures.base import FixtureBase
from parrot.fixtures.moving_head import MovingHead
from parrot.interpreters.base import InterpreterBase


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


@beartype
class StrobeChannelSustained(InterpreterBase[FixtureBase]):
    """Drives only the strobe DMX channel high; leaves dimmer/color to other interpreters."""

    hype = 90

    def step(self, frame: Frame, scheme: ColorScheme) -> None:
        for i in self.group:
            i.set_strobe(220)

    def exit(self, frame: Frame, scheme: ColorScheme) -> None:
        for i in self.group:
            i.set_strobe(0)
