from __future__ import annotations

from beartype import beartype

from parrot.fixtures.chauvet.colorband_pix import ChauvetColorBandPiX_36Ch
from parrot.fixtures.moving_head import MovingHead
from parrot.interpreters.base import (
    ColorAlternateBg,
    ColorBg,
    ColorFg,
    ColorRainbow,
    InterpreterArgs,
    InterpreterBase,
    Noop,
    with_args,
)
from parrot.director.color_scheme import ColorScheme
from parrot.director.frame import Frame
from parrot.director.mode import Mode
from parrot.interpreters.motionstrip import PanLatched
from parrot.interpreters.movers import (
    MoverGobo,
    MoverNoGobo,
    MoverRandomGobo,
)
from parrot.interpreters.rotosphere import (
    Spin,
    RotosphereSpinColor,
)
from parrot.interpreters.slow import (
    SlowDecay,
    SlowSustained,
    VerySlowDecay,
)
from parrot.fixtures.laser import Laser
from typing import List, Dict, Union, Tuple, Type
from parrot.fixtures.base import FixtureBase
from parrot.fixtures.mirrorball import Mirrorball
from parrot.fixtures.motionstrip import Motionstrip
from parrot.interpreters.latched import (
    DimmerFadeLatched,
    DimmerFadeLatched4s,
    DimmerFadeLatchedRandom,
)
from parrot.interpreters.dimmer import (
    Dimmer255,
    DimmerFadeIn,
    DimmerFadeInLinearSeconds,
    DimmersBeatChase,
    GentlePulse,
    LightningStab,
    SequenceDimmers,
    SequenceFadeDimmers,
    StabPulse,
    Twinkle,
)
from parrot.interpreters.combo import combo

from parrot.interpreters.dimmer import Dimmer0
from parrot.interpreters.randomize import randomize, weighted_randomize
from parrot.fixtures.chauvet.rotosphere import ChauvetRotosphere_28Ch
from parrot.interpreters.bulbs import AllBulbs255, for_bulbs
from parrot.interpreters.laser import LaserLatch
from parrot.interpreters.spatial import (
    HardSpatialPulse,
    SoftSpatialPulse,
    HardSpatialCenterOutPulse,
)
from parrot.interpreters.strobe import StrobeHighSustained
from parrot.interpreters.signal import signal_switch
from parrot.fixtures.led_par import Par
from parrot.fixtures.chauvet.derby import ChauvetDerby
from parrot.interpreters.move import (
    MoveCircleSync,
    MoveCircles,
    MoveCirclesPhased,
    MoveFan,
    MoveFigureEight,
    MoveNod,
)
from parrot.interpreters.mode_test_interpreters import RigColorCycle


@beartype
def _fixture_cloud_group_casefold(fixture: FixtureBase) -> str | None:
    raw = getattr(fixture, "cloud_group_name", None)
    if raw is None or not isinstance(raw, str):
        return None
    s = raw.strip()
    return s.casefold() if s else None


class Group:
    """DSL matcher for fixtures by their cloud group name (case-insensitive, trimmed)."""

    def __init__(self, name: str):
        self.name = name
        self._key = name.strip().casefold()

    def matches(self, fixture: FixtureBase) -> bool:
        return _fixture_cloud_group_casefold(fixture) == self._key

    def __hash__(self) -> int:
        return hash(("Group", self._key))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Group) and other._key == self._key

    def __repr__(self) -> str:
        return f"Group({self.name!r})"


Matcher = Union[Type[FixtureBase], Group, Tuple["Matcher", ...]]


def _matcher_matches(matcher: Matcher, fixture: FixtureBase) -> bool:
    if isinstance(matcher, Group):
        return matcher.matches(fixture)
    if isinstance(matcher, tuple):
        return all(_matcher_matches(m, fixture) for m in matcher)
    return isinstance(fixture, matcher)


def _mode_has_matcher(mapping: dict) -> bool:
    """True if any key uses the `Group` DSL matcher (requires flat-list dispatch)."""

    def _contains_group(key: object) -> bool:
        if isinstance(key, Group):
            return True
        if isinstance(key, tuple):
            return any(_contains_group(k) for k in key)
        return False

    return any(_contains_group(k) for k in mapping)


@beartype
class CompositeInterpreter(InterpreterBase[FixtureBase]):
    """Runs child interpreters in order; used when a mode partitions a flat fixture list."""

    def __init__(
        self,
        group: list[FixtureBase],
        args: InterpreterArgs,
        children: list[InterpreterBase],
    ):
        super().__init__(group, args)
        self._children = children

    def step(self, frame: Frame, scheme: ColorScheme) -> None:
        for c in self._children:
            c.step(frame, scheme)

    def exit(self, frame: Frame, scheme: ColorScheme) -> None:
        for c in self._children:
            c.exit(frame, scheme)

    def __str__(self) -> str:
        return " | ".join(str(c) for c in self._children)


# `get_interpreter` must match subclasses before Par — Mirrorball is a Par subclass.
_INTERPRETER_TYPE_ORDER: Tuple[Type[FixtureBase], ...] = (
    Mirrorball,
    MovingHead,
    Motionstrip,
    ChauvetColorBandPiX_36Ch,
    Laser,
    ChauvetRotosphere_28Ch,
    ChauvetDerby,
    Par,
)


def _sorted_mode_interpretation_items(
    phrase: Mode,
) -> List[Tuple[Matcher, List[InterpreterBase]]]:
    d = mode_interpretations[phrase]
    rank = {cls: i for i, cls in enumerate(_INTERPRETER_TYPE_ORDER)}

    def sort_key(item: Tuple[Matcher, List[InterpreterBase]]) -> Tuple[int, int, str]:
        k = item[0]
        # Most specific first: (Group + class) > bare Group > bare class (subclass-aware).
        if isinstance(k, tuple):
            cls = next((m for m in k if isinstance(m, type)), None)
            return (0, rank.get(cls, 1000) if cls else 0, repr(k))
        if isinstance(k, Group):
            return (1, 0, k.name)
        return (2, rank.get(k, 1000), k.__name__)

    return sorted(d.items(), key=sort_key)


mode_interpretations: Dict[
    Mode,
    Dict[FixtureBase, List[InterpreterBase]],
] = {
    Mode.blackout: {},
    Mode.chill: {
        Mirrorball: [Dimmer0],
        Par: [
            combo(
                signal_switch(
                    randomize(
                        SequenceFadeDimmers,
                        GentlePulse,
                        Twinkle,
                    )
                ),
                ColorBg,
            )
        ],
        MovingHead: [
            # Dimmer0,
            combo(
                signal_switch(
                    randomize(
                        SequenceFadeDimmers,
                        GentlePulse,
                        VerySlowDecay,
                        SlowSustained,
                        SoftSpatialPulse,
                    )
                ),
                ColorBg,
                randomize(MoveCircles, MoveNod, MoveFigureEight, MoveFan),
            )
        ],
        Motionstrip: [
            Dimmer0
            # combo(
            #     signal_switch(
            #         randomize(
            #             combo(Dimmer255, for_bulbs(Twinkle)),
            #             combo(DimmersBeatChase, AllBulbs255),
            #             combo(SlowDecay, AllBulbs255),
            #             combo(
            #                 Dimmer255,
            #                 for_bulbs(
            #                     with_args(
            #                         "GentlePulseTrigger0.1",
            #                         GentlePulse,
            #                         trigger_level=0.1,
            #                     )
            #                 ),
            #             ),
            #             combo(Dimmer255, for_bulbs(DimmersBeatChase)),
            #         ),
            #     ),
            #     randomize(ColorFg, ColorAlternateBg, ColorBg, for_bulbs(ColorRainbow)),
            #     randomize(PanLatched, MoveCircles),
            # ),
        ],
        ChauvetColorBandPiX_36Ch: [
            combo(
                signal_switch(
                    randomize(
                        for_bulbs(SequenceFadeDimmers),
                        for_bulbs(GentlePulse),
                        VerySlowDecay,
                        SlowSustained,
                        for_bulbs(Twinkle),
                    )
                ),
                ColorBg,
            )
        ],
        Laser: [signal_switch(Dimmer0)],
        ChauvetRotosphere_28Ch: [
            combo(signal_switch(randomize(GentlePulse, Twinkle)), ColorBg)
        ],
        ChauvetDerby: [combo(signal_switch(randomize(GentlePulse, Twinkle)), ColorBg)],
    },
    Mode.rave_gentle: {
        Mirrorball: [Dimmer0],
        Par: [
            combo(
                signal_switch(
                    randomize(
                        SequenceFadeDimmers,
                        GentlePulse,
                        Twinkle,
                    )
                ),
                ColorBg,
            )
        ],
        MovingHead: [
            combo(
                signal_switch(
                    randomize(
                        SequenceFadeDimmers,
                        GentlePulse,
                        VerySlowDecay,
                        SlowSustained,
                        SoftSpatialPulse,
                    )
                ),
                ColorBg,
                randomize(MoveCircles, MoveNod, MoveFigureEight, MoveFan),
            )
        ],
        Motionstrip: [
            combo(
                signal_switch(
                    randomize(
                        combo(
                            randomize(
                                SequenceFadeDimmers,
                                GentlePulse,
                                Twinkle,
                            ),
                            AllBulbs255,
                        ),
                        combo(
                            Dimmer255,
                            for_bulbs(
                                randomize(
                                    SequenceFadeDimmers,
                                    GentlePulse,
                                    Twinkle,
                                )
                            ),
                        ),
                    ),
                ),
                randomize(ColorFg, ColorAlternateBg, ColorBg, for_bulbs(ColorRainbow)),
                randomize(MoveCircles, MoveFan),
            ),
        ],
        ChauvetColorBandPiX_36Ch: [
            combo(
                signal_switch(
                    randomize(
                        for_bulbs(SequenceFadeDimmers),
                        for_bulbs(GentlePulse),
                        VerySlowDecay,
                        SlowSustained,
                        for_bulbs(Twinkle),
                    )
                ),
                ColorBg,
            )
        ],
        Laser: [signal_switch(Dimmer0)],
        ChauvetRotosphere_28Ch: [
            combo(signal_switch(randomize(GentlePulse, Twinkle)), ColorBg)
        ],
        ChauvetDerby: [combo(signal_switch(randomize(GentlePulse, Twinkle)), ColorBg)],
    },
    Mode.rave: {
        Mirrorball: [Dimmer0],
        Par: [
            combo(
                signal_switch(
                    randomize(
                        StabPulse,
                        LightningStab,
                    ),
                ),
                randomize(ColorAlternateBg, ColorBg, ColorRainbow),
            ),
        ],
        MovingHead: [
            combo(
                signal_switch(
                    randomize(
                        HardSpatialPulse,
                        HardSpatialCenterOutPulse,
                        DimmersBeatChase,
                        SlowDecay,
                        GentlePulse,
                        DimmerFadeLatched,
                        SequenceDimmers,
                        SequenceFadeDimmers,
                        StabPulse,
                        LightningStab,
                    ),
                ),
                weighted_randomize((95, ColorFg), (5, ColorRainbow)),
                randomize(MoveCircles, MoveNod, MoveFigureEight, MoveFan),
                weighted_randomize(
                    (10, with_args("StarburstGobo", MoverGobo, gobo="starburst")),
                    (90, MoverNoGobo),
                ),
            )
        ],
        Motionstrip: [
            combo(
                signal_switch(
                    randomize(
                        combo(Dimmer255, for_bulbs(Twinkle)),
                        combo(DimmersBeatChase, AllBulbs255),
                        combo(Dimmer255, for_bulbs(DimmersBeatChase)),
                        combo(Dimmer255, for_bulbs(StabPulse)),
                        combo(LightningStab, for_bulbs(LightningStab)),
                    ),
                ),
                randomize(ColorFg, ColorAlternateBg, ColorBg, for_bulbs(ColorRainbow)),
                randomize(MoveCircles, MoveFan),
            ),
        ],
        ChauvetColorBandPiX_36Ch: [
            combo(
                signal_switch(
                    randomize(
                        combo(Dimmer255, for_bulbs(Twinkle)),
                        combo(DimmersBeatChase, AllBulbs255),
                        combo(SlowDecay, AllBulbs255),
                        combo(
                            Dimmer255,
                            for_bulbs(
                                with_args(
                                    "GentlePulseTrigger0.1",
                                    GentlePulse,
                                    trigger_level=0.1,
                                )
                            ),
                        ),
                        combo(Dimmer255, for_bulbs(DimmersBeatChase)),
                    ),
                ),
                randomize(ColorFg, ColorAlternateBg, ColorBg, for_bulbs(ColorRainbow)),
            ),
        ],
        Laser: [signal_switch(LaserLatch), StrobeHighSustained],
        ChauvetRotosphere_28Ch: [
            combo(
                RotosphereSpinColor,
                randomize(
                    DimmerFadeIn,
                    for_bulbs(Twinkle),
                    for_bulbs(GentlePulse),
                    DimmerFadeLatched4s,
                    SlowSustained,
                ),
            ),
            combo(
                for_bulbs(ColorRainbow),
                Spin,
                VerySlowDecay,
            ),
        ],
        ChauvetDerby: [
            combo(
                randomize(Spin, Noop),
                randomize(ColorAlternateBg, ColorFg),
                randomize(
                    GentlePulse,
                    DimmerFadeLatched,
                    DimmerFadeLatched4s,
                    SlowDecay,
                    Dimmer0,
                ),
            ),
        ],
    },
    Mode.ethereal: {
        Mirrorball: [
            with_args("MirrorballFade10s", DimmerFadeInLinearSeconds, seconds=10.0)
        ],
        (Group("sheer lights"), MovingHead): [
            combo(
                GentlePulse,
                ColorAlternateBg,
                with_args("EtherealPhasedCircles", MoveCirclesPhased, multiplier=0.16),
                MoverRandomGobo,
            )
        ],
        Group("sheer lights"): [combo(Dimmer255, ColorAlternateBg)],
    },
    Mode.test: {
        Mirrorball: [Dimmer0],
        Par: [combo(Dimmer255, RigColorCycle)],
        MovingHead: [combo(Dimmer255, RigColorCycle, MoveCircleSync, MoverNoGobo)],
        Motionstrip: [combo(Dimmer255, RigColorCycle)],
        ChauvetColorBandPiX_36Ch: [combo(Dimmer255, for_bulbs(RigColorCycle))],
        Laser: [combo(Dimmer255, RigColorCycle)],
        ChauvetRotosphere_28Ch: [combo(Dimmer255, RigColorCycle)],
        ChauvetDerby: [combo(Dimmer255, RigColorCycle)],
    },
}


def mode_uses_group_matchers(phrase: Mode) -> bool:
    """Modes whose DSL uses `Group(...)` keys must receive the whole patch flat."""
    return _mode_has_matcher(mode_interpretations.get(phrase, {}))


def get_interpreter(
    phrase: Mode,
    fixture_group: List[FixtureBase],
    args: InterpreterArgs,
) -> InterpreterBase:
    """Pick the interpreter(s) for a group of fixtures under ``phrase``.

    Modes with only fixture-class keys expect a homogeneous list; the first
    matching class entry wins. Modes using :class:`Group` matchers receive the
    flat patch and are partitioned across all keys in insertion order; any
    leftover fixture gets :class:`Dimmer0`.
    """
    items = _sorted_mode_interpretation_items(phrase)

    if not mode_uses_group_matchers(phrase):
        for key, options in items:
            if fixture_group and _matcher_matches(key, fixture_group[0]):
                return randomize(*options)(fixture_group, args)
        return Dimmer0(fixture_group, args)

    children: list[InterpreterBase] = []
    remaining = list(fixture_group)
    for key, options in items:
        matched = [f for f in remaining if _matcher_matches(key, f)]
        if not matched:
            continue
        matched_ids = {id(f) for f in matched}
        remaining = [f for f in remaining if id(f) not in matched_ids]
        children.append(randomize(*options)(matched, args))
    if remaining:
        children.append(Dimmer0(remaining, args))
    if len(children) == 1:
        return children[0]
    return CompositeInterpreter(fixture_group, args, children)
