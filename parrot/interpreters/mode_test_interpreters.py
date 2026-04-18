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


@beartype
class PanTiltAxisCheck(InterpreterBase):
    """Pan/tilt axis check for rig debugging.

    Visits each DMX extreme one axis at a time, returning to the mid-range
    ``(pan=127, tilt=127)`` between each extreme so you can reason about one
    degree of freedom per step:

        (127, 127) → (127, 255)  tilt up
                   → (127, 127)  center
                   → (127,   0)  tilt down
                   → (127, 127)  center
                   → (  0, 127)  pan left
                   → (127, 127)  center
                   → (255, 127)  pan right
                   → (127, 127)  center

    Each state holds for ``SECONDS_PER_STEP`` so the movement is easy to see on
    physical fixtures. All fixtures in the group move in sync.
    """

    SECONDS_PER_STEP = 1.5

    # (pan, tilt) per step. Order matches the docstring above so the rig walks
    # tilt-up, tilt-down, pan-left, pan-right with a recenter between each.
    SEQUENCE = (
        (127, 127),
        (127, 255),
        (127, 127),
        (127, 0),
        (127, 127),
        (0, 127),
        (127, 127),
        (255, 127),
    )

    def __str__(self) -> str:
        return "🧭 PanTiltAxisCheck"

    def step(self, frame: Frame, scheme: ColorScheme) -> None:
        idx = int(frame.time / self.SECONDS_PER_STEP) % len(self.SEQUENCE)
        pan, tilt = self.SEQUENCE[idx]
        for fixture in self.group:
            fixture.set_pan(pan)
            fixture.set_tilt(tilt)
