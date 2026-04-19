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

    Walks each of the four DMX extremes one at a time, linearly interpolating
    between positions so the motion is easy to follow on a physical fixture.
    One excursion for a single extreme has four equal-length phases:

        0   : hold at home (127, 127)          for ``HOLD_SECONDS``
        1   : lerp home → extreme              over ``TRAVEL_SECONDS``
        2   : hold at extreme                  for ``HOLD_SECONDS``
        3   : lerp extreme → home              over ``TRAVEL_SECONDS``

    The four extremes are visited in order ``tilt up → tilt down → pan left →
    pan right``; after the fourth excursion the cycle loops. All fixtures in
    the group move in sync.
    """

    HOME = (127, 127)
    EXTREMES = (
        (127, 255),  # tilt up
        (127, 0),    # tilt down
        (0, 127),    # pan left
        (255, 127),  # pan right
    )

    HOLD_SECONDS = 1.0
    TRAVEL_SECONDS = 1.0

    def __str__(self) -> str:
        return "🧭 PanTiltAxisCheck"

    @classmethod
    def _cycle_seconds(cls) -> float:
        """Duration of one (hold-home → travel-out → hold-extreme → travel-back) excursion."""
        return 2 * cls.HOLD_SECONDS + 2 * cls.TRAVEL_SECONDS

    @classmethod
    def position_at(cls, t: float) -> tuple[float, float]:
        """Resolve pan/tilt at absolute time ``t`` so tests can verify every phase."""
        cycle = cls._cycle_seconds()
        total = cycle * len(cls.EXTREMES)
        t_mod = t % total
        idx = int(t_mod // cycle)
        local = t_mod - idx * cycle
        target = cls.EXTREMES[idx]
        hold = cls.HOLD_SECONDS
        travel = cls.TRAVEL_SECONDS

        if local < hold:
            return (float(cls.HOME[0]), float(cls.HOME[1]))
        if local < hold + travel:
            u = (local - hold) / travel
            return (
                float(cls.HOME[0] + (target[0] - cls.HOME[0]) * u),
                float(cls.HOME[1] + (target[1] - cls.HOME[1]) * u),
            )
        if local < hold + travel + hold:
            return (float(target[0]), float(target[1]))
        u = (local - hold - travel - hold) / travel
        return (
            float(target[0] + (cls.HOME[0] - target[0]) * u),
            float(target[1] + (cls.HOME[1] - target[1]) * u),
        )

    def step(self, frame: Frame, scheme: ColorScheme) -> None:
        pan, tilt = self.position_at(frame.time)
        for fixture in self.group:
            fixture.set_pan(pan)
            fixture.set_tilt(tilt)
