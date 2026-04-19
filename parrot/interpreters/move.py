import math
from beartype import beartype
from parrot.interpreters.base import InterpreterBase, InterpreterArgs
from parrot.fixtures.base import FixtureBase
from colorama import Fore, Style


def _even_phase_spread(n: int) -> list[float]:
    """Evenly spaced phases around the unit circle: ``[i / N * 2π for i in 0..N]``.

    Shared by every group-move interpreter in this module so that a group of
    movers always visibly covers the whole cycle at once, regardless of group
    size. Deterministic (no RNG) so regenerations look stable.
    """
    n = max(n, 1)
    return [i / n * 2.0 * math.pi for i in range(n)]


@beartype
class MoveCircles(InterpreterBase):
    """Pan/tilt circles with a deterministic phase offset per group index.

    Each fixture in the group gets an evenly spaced phase around the unit circle
    (``i / N * 2π``), so the group traces the same circle with fixtures
    equidistantly staggered in time. Deterministic phasing keeps the look stable
    across regenerations and avoids the occasional "all bunched up" roll that
    random phasing can produce with small groups.
    """

    def __init__(
        self,
        group: list[FixtureBase],
        args: InterpreterArgs,
        multiplier: float = 1.0,
    ):
        super().__init__(group, args)
        self.multiplier = multiplier
        self._phase = _even_phase_spread(len(group))

    def __str__(self):
        return f"🔄 {Fore.GREEN}Circles{Style.RESET_ALL}"

    def step(self, frame, scheme):
        for i, fixture in enumerate(self.group):
            t = frame.time * self.multiplier + self._phase[i]
            fixture.set_pan(math.cos(t) * 127 + 128)
            fixture.set_tilt(math.sin(t) * 127 + 128)


@beartype
class MoveNod(InterpreterBase):
    """Tilt-only nod with an evenly spaced per-fixture phase.

    Fixtures share one tilt oscillator but start at phases ``i / N * 2π`` around
    its cycle, so the group covers a full up-down wave at any given moment
    instead of nodding in unison. Pan stays centered.
    """

    def __init__(
        self,
        group: list[FixtureBase],
        args: InterpreterArgs,
        multiplier: float = 1.0,
    ):
        super().__init__(group, args)
        self.multiplier = multiplier
        self._phase = _even_phase_spread(len(group))

    def __str__(self):
        return f"⬆️⬇️ {Fore.GREEN}Nod{Style.RESET_ALL}"

    def step(self, frame, scheme):
        for i, fixture in enumerate(self.group):
            fixture.set_pan(128)
            fixture.set_tilt(
                math.sin(frame.time * self.multiplier + self._phase[i]) * 127 + 128
            )


@beartype
class MoveFigureEight(InterpreterBase):
    """Lissajous figure-eight with an evenly spaced per-fixture phase.

    Pan follows ``sin(t)`` and tilt follows ``sin(2t)`` (pan period 2π is the
    limiting cycle), so spreading phase as ``i / N * 2π`` staggers fixtures
    evenly around the figure-eight path.
    """

    def __init__(
        self,
        group: list[FixtureBase],
        args: InterpreterArgs,
        multiplier: float = 1.0,
    ):
        super().__init__(group, args)
        self.multiplier = multiplier
        self._phase = _even_phase_spread(len(group))

    def __str__(self):
        return f"∞ {Fore.GREEN}FigureEight{Style.RESET_ALL}"

    def step(self, frame, scheme):
        for i, fixture in enumerate(self.group):
            t = frame.time * self.multiplier + self._phase[i]
            fixture.set_pan(math.sin(t) * 127 + 128)
            fixture.set_tilt(math.sin(2 * t) * 127 + 128)


@beartype
class MoveCircleSync(InterpreterBase):
    """Pan/tilt circle with identical motion on every fixture (no per-fixture phase / fanning)."""

    def __init__(
        self,
        group: list[FixtureBase],
        args: InterpreterArgs,
        multiplier: float = 0.35,
        phase: float = 0.0,
    ):
        super().__init__(group, args)
        self.multiplier = multiplier
        self.phase = phase

    def __str__(self) -> str:
        return f"🔄 {Fore.GREEN}CircleSync{Style.RESET_ALL}"

    def step(self, frame, scheme):
        t = frame.time * self.multiplier + self.phase
        pan = math.cos(t) * 127 + 128
        tilt = math.sin(t) * 127 + 128
        for fixture in self.group:
            fixture.set_pan(pan)
            fixture.set_tilt(tilt)


@beartype
class MoveFan(InterpreterBase):
    """Pan fan with a spatial amplitude AND a temporal phase spread.

    Each fixture's pan swings with an amplitude proportional to its position
    from the centre of the group (``rel_pos``), giving the classic fan open /
    close look. On top of that we add an evenly spaced per-fixture phase (``i
    / N * 2π``) so that at any single moment fixtures are at different points
    in the oscillator instead of all crossing centre together — the fan breathes
    as a wave through the group rather than snapping open and closed in unison.

    With odd group sizes the geometric centre fixture still has ``rel_pos == 0``
    so its pan collapses to 128 regardless of phase, preserving the old
    "centre fixture stays put" behaviour.
    """

    def __init__(
        self,
        group: list[FixtureBase],
        args: InterpreterArgs,
        multiplier: float = 1.0,
        spread: float = 1.0,
    ):
        super().__init__(group, args)
        self.multiplier = multiplier
        self.spread = spread
        self._phase = _even_phase_spread(len(group))

    def __str__(self):
        return f"↔️ {Fore.GREEN}Fan{Style.RESET_ALL}"

    def step(self, frame, scheme):
        middle_idx = (len(self.group) - 1) / 2

        for idx, fixture in enumerate(self.group):
            rel_pos = (idx - middle_idx) / (middle_idx + 0.00001)
            pan = (
                math.sin(frame.time * self.multiplier + self._phase[idx])
                * rel_pos
                * self.spread
                * 127
                + 128
            )
            fixture.set_pan(pan)
            fixture.set_tilt(128)


@beartype
class MoveSmoothWalk(InterpreterBase):
    """Smooth wandering via phase-offset sums of sines on pan and tilt.

    Each axis uses two incommensurate frequencies so the beam draws a smooth
    quasi-Lissajous path on a wall (C∞, no kinks). Pan and tilt use separate
    phase ladders from :func:`_even_phase_spread` plus a fixed tilt offset so
    fixtures fan across the group like :class:`MoveCircles` but with richer
    2D curves than a single circle.

    ``multiplier`` scales how fast paths evolve in time (lower = slower drift).
    """

    _W_SLOW = 1.0
    _W_FAST = 0.618
    _W_TILT_SLOW = 0.834
    _W_TILT_FAST = 0.377
    _A_MAJOR = 78.0
    _A_MINOR = 42.0

    def __init__(
        self,
        group: list[FixtureBase],
        args: InterpreterArgs,
        multiplier: float = 0.2,
    ):
        super().__init__(group, args)
        self.multiplier = multiplier
        self._phase_pan = _even_phase_spread(len(group))
        self._phase_tilt = [p + math.pi * 0.5 for p in self._phase_pan]

    def __str__(self) -> str:
        return f"🚶 {Fore.GREEN}SmoothWalk{Style.RESET_ALL}"

    def step(self, frame, scheme):
        t = frame.time * self.multiplier
        for i, fixture in enumerate(self.group):
            phi = self._phase_pan[i]
            psi = self._phase_tilt[i]
            pan = (
                128.0
                + self._A_MAJOR * math.sin(self._W_SLOW * t + phi)
                + self._A_MINOR * math.sin(self._W_FAST * 1.31 * t + phi + 0.7)
            )
            tilt = (
                128.0
                + self._A_MAJOR * math.sin(self._W_TILT_SLOW * t + psi)
                + self._A_MINOR * math.sin(self._W_TILT_FAST * 1.27 * t + psi + 1.05)
            )
            fixture.set_pan(max(1.0, min(255.0, pan)))
            fixture.set_tilt(max(1.0, min(255.0, tilt)))
