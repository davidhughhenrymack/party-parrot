"""Interpreters for Mode.test (fixture / rig checkout)."""

from beartype import beartype

from parrot.director.color_scheme import ColorScheme
from parrot.director.frame import Frame
from parrot.interpreters.base import InterpreterBase
from parrot.utils.colour import Color


@beartype
class RigColorCycle(InterpreterBase):
    """Cycle white → red → green → blue every few seconds (same color for the whole group)."""

    COLORS = (
        Color("white"),
        Color("red"),
        Color("green"),
        Color("blue"),
    )
    SECONDS_PER_COLOR = 5.0

    def __str__(self) -> str:
        return "🧪 RigColorCycle"

    def step(self, frame: Frame, scheme: ColorScheme) -> None:
        idx = int(frame.time / self.SECONDS_PER_COLOR) % len(self.COLORS)
        c = self.COLORS[idx]
        for fixture in self.group:
            fixture.set_color(c)
