from beartype import beartype
from parrot.director.color_scheme import ColorScheme
from parrot.director.frame import Frame
from parrot.fixtures.base import FixtureBase
from parrot.interpreters.base import InterpreterArgs, InterpreterBase


@beartype
class StrobeOn(InterpreterBase[FixtureBase]):
    def __init__(
        self,
        group: list[FixtureBase],
        args: InterpreterArgs,
        strobe_value: int = 220,
    ):
        super().__init__(group, args)
        self.strobe_value = strobe_value

    def step(self, frame, scheme):
        for i in self.group:
            i.set_strobe(self.strobe_value)

    def exit(self, frame: Frame, scheme: ColorScheme):
        for i in self.group:
            i.clear_strobe()


@beartype
class StrobeOff(InterpreterBase[FixtureBase]):
    def step(self, frame, scheme):
        for i in self.group:
            i.clear_strobe()


@beartype
class StrobeHighSustained(InterpreterBase[FixtureBase]):
    def __init__(
        self,
        group: list[FixtureBase],
        args: InterpreterArgs,
        strobe_value: int = 220,
    ):
        super().__init__(group, args)
        self.strobe_value = strobe_value

    def step(self, frame, scheme):
        for i in self.group:
            i.set_strobe(self.strobe_value)
            i.set_dimmer(255)

    def exit(self, frame: Frame, scheme: ColorScheme):
        for i in self.group:
            i.clear_strobe()
            i.set_dimmer(0)


@beartype
class StrobeChannelSustained(InterpreterBase[FixtureBase]):
    """Drives only the strobe DMX channel high; leaves dimmer/color to other interpreters."""

    def __init__(
        self,
        group: list[FixtureBase],
        args: InterpreterArgs,
        strobe_value: int = 220,
    ):
        super().__init__(group, args)
        self.strobe_value = strobe_value

    def step(self, frame: Frame, scheme: ColorScheme) -> None:
        for i in self.group:
            i.set_strobe(self.strobe_value)

    def exit(self, frame: Frame, scheme: ColorScheme) -> None:
        for i in self.group:
            i.clear_strobe()
