"""Mode → (fixture matcher → interpreter options) expression.

This file is intentionally just the DSL data. The matching/dispatch machinery
(how a matcher resolves, how a ``Mode`` plus a fixture group becomes an
``InterpreterBase``) lives in :mod:`parrot.director.mode_dispatch`.
"""

from __future__ import annotations

from typing import Dict, List

from parrot.director.frame import FrameSignal
from parrot.director.mode import Mode
from parrot.director.mode_dispatch import Group, Matcher
from parrot.fixtures.chauvet.colorband_pix import ChauvetColorBandPiX_36Ch
from parrot.fixtures.chauvet.derby import ChauvetDerby
from parrot.fixtures.chauvet.rotosphere import ChauvetRotosphere_28Ch
from parrot.fixtures.laser import Laser
from parrot.fixtures.led_par import Par
from parrot.fixtures.mirrorball import Mirrorball
from parrot.fixtures.motionstrip import Motionstrip
from parrot.fixtures.moving_head import MovingHead
from parrot.interpreters.base import (
    AnyColor,
    ColorAlternateBg,
    ColorBg,
    InterpreterBase,
    Noop,
    with_args,
)
from parrot.interpreters.bulbs import AllBulbs255, for_bulbs
from parrot.interpreters.combo import combo
from parrot.interpreters.dimmer import (
    Dimmer0,
    Dimmer255,
    DimmerFadeIn,
    DimmerFadeInLinearSeconds,
    DimmersBeatChase,
    GentlePulse,
    LightningStab,
    SequenceDimmers,
    SequenceFadeDimmers,
    SlowBreath,
    StabPulse,
    Twinkle,
)
from parrot.interpreters.laser import LaserLatch
from parrot.interpreters.latched import (
    DimmerFadeLatched,
    DimmerFadeLatched4s,
)
from parrot.interpreters.mode_test_interpreters import (
    PanTiltAxisCheck,
    RigColorCycle,
)
from parrot.interpreters.move import (
    MoveCircles,
    MoveFan,
    MoveFigureEight,
    MoveNod,
    MoveSmoothWalk,
)
from parrot.interpreters.movers import (
    FocusBig,
    FocusSmall,
    MoverGobo,
    MoverNoGobo,
    MoverRandomGobo,
    PrismOff,
    RotatePrism,
    RotatingGobo,
)
from parrot.interpreters.randomize import randomize, weighted_randomize
from parrot.interpreters.rotosphere import (
    RotosphereSpinColor,
    Spin,
)
from parrot.interpreters.signal import signal_switch
from parrot.interpreters.slow import (
    SlowDecay,
    SlowSustained,
    VerySlowDecay,
)
from parrot.interpreters.spatial import (
    HardSpatialCenterOutPulse,
    HardSpatialPulse,
    SoftSpatialPulse,
)
from parrot.interpreters.strobe import StrobeChannelSustained, StrobeHighSustained


mode_interpretations: Dict[Mode, Dict[Matcher, List[InterpreterBase]]] = {
    Mode.blackout: {},
    Mode.chill: {
        # Sheer lights are an ethereal-mode-only feature; keep them dark elsewhere (all types).
        Group("sheer lights"): [Dimmer0],
        Mirrorball: [Dimmer0],
        Par: [
            combo(
                ColorBg,
                signal_switch(
                    randomize(
                        SequenceFadeDimmers,
                        GentlePulse,
                        Twinkle,
                    )
                ),
            )
        ],
        MovingHead: [
            combo(
                ColorBg,
                signal_switch(
                    randomize(
                        SequenceFadeDimmers,
                        VerySlowDecay,
                        SlowSustained,
                        SequenceFadeDimmers,
                    )
                ),
                randomize(
                    with_args("ChillCircles", MoveCircles, multiplier=0.25),
                    with_args("ChillNod", MoveNod, multiplier=0.25),
                    with_args("ChillFigureEight", MoveFigureEight, multiplier=0.25),
                    with_args("ChillFan", MoveFan, multiplier=0.25),
                    with_args(
                        "ChillSmoothWalk",
                        MoveSmoothWalk,
                        multiplier=0.05,
                    ),
                ),
                randomize(MoverRandomGobo, MoverNoGobo),
                randomize(RotatePrism, PrismOff),
                randomize(FocusBig, FocusSmall),
            )
        ],
        Motionstrip: [Dimmer0],
        ChauvetColorBandPiX_36Ch: [
            combo(
                randomize(ColorBg, ColorAlternateBg),
                signal_switch(
                    randomize(
                        for_bulbs(SequenceFadeDimmers),
                        for_bulbs(GentlePulse),
                        VerySlowDecay,
                        SlowSustained,
                        for_bulbs(Twinkle),
                    )
                ),
            )
        ],
        Laser: [signal_switch(Dimmer0)],
        ChauvetRotosphere_28Ch: [
            combo(ColorBg, signal_switch(randomize(GentlePulse, Twinkle)))
        ],
        ChauvetDerby: [combo(ColorBg, signal_switch(randomize(GentlePulse, Twinkle)))],
    },
    Mode.rave: {
        # Rave sheer movers share one dimmer / color / move / gobo pick across the
        # whole group, plus a random focus width (big vs. small beam) and a random
        # prism state (spinning prism vs. off). Picking per-group rather than
        # per-fixture keeps all the beams reading as one cohesive look, and each
        # reshuffle flips the character of the rig in one decision.
        #
        # Sheer lights should feel like a rare accent, not a constant presence —
        # wrap the whole combo in a 30/70 weighted pick against Dimmer0 so each
        # reshuffle keeps the sheer movers dark ~70% of the time and only
        # occasionally brings them into play for the rave look.
        (Group("sheer lights"), MovingHead): [
            weighted_randomize(
                (
                    30,
                    combo(
                        AnyColor,
                        signal_switch(
                            randomize(
                                HardSpatialPulse,
                                HardSpatialCenterOutPulse,
                                DimmersBeatChase,
                                GentlePulse,
                                with_args(
                                    "GentlePulseHigh",
                                    GentlePulse,
                                    signal=FrameSignal.freq_high,
                                ),
                                DimmerFadeLatched,
                                SequenceDimmers,
                                SequenceFadeDimmers,
                                StabPulse,
                                with_args(
                                    "StabPulseHigh",
                                    StabPulse,
                                    signal=FrameSignal.freq_high,
                                ),
                                LightningStab,
                            ),
                        ),
                        randomize(
                            MoveCircles,
                            MoveNod,
                            MoveFigureEight,
                            MoveFan,
                            MoveSmoothWalk,
                        ),
                        weighted_randomize(
                            (
                                10,
                                with_args("StarburstGobo", MoverGobo, gobo="starburst"),
                            ),
                            (90, MoverNoGobo),
                        ),
                        randomize(FocusBig, FocusSmall),
                        randomize(RotatePrism, PrismOff),
                    ),
                ),
                (70, Dimmer0),
            )
        ],
        Group("sheer lights"): [Dimmer0],
        # Mirrorball stays dark most of the time in rave mode; ~10% of
        # reshuffles bring it in as a beat-triggered StabPulse tinted with the
        # scheme foreground colour for a sudden spotlight-on-the-disco-ball hit.
        Mirrorball: [
            weighted_randomize(
                (10, combo(StabPulse, AnyColor)),
                (90, Dimmer0),
            )
        ],
        Par: [
            combo(
                AnyColor,
                signal_switch(
                    randomize(
                        StabPulse,
                        with_args(
                            "StabPulseHigh",
                            StabPulse,
                            signal=FrameSignal.freq_high,
                        ),
                        LightningStab,
                    ),
                ),
            ),
        ],
        MovingHead: [
            combo(
                AnyColor,
                signal_switch(
                    randomize(
                        HardSpatialPulse,
                        HardSpatialCenterOutPulse,
                        DimmersBeatChase,
                        GentlePulse,
                        with_args(
                            "GentlePulseHigh",
                            GentlePulse,
                            signal=FrameSignal.freq_high,
                        ),
                        DimmerFadeLatched,
                        SequenceDimmers,
                        SequenceFadeDimmers,
                        StabPulse,
                        with_args(
                            "StabPulseHigh",
                            StabPulse,
                            signal=FrameSignal.freq_high,
                        ),
                        LightningStab,
                    ),
                ),
                randomize(
                    MoveCircles, MoveNod, MoveFigureEight, MoveFan, MoveSmoothWalk
                ),
                weighted_randomize(
                    (10, MoverRandomGobo),
                    (90, MoverNoGobo),
                ),
                weighted_randomize(
                    (10, FocusBig),
                    (90, FocusSmall),
                ),
                weighted_randomize(
                    (10, RotatePrism),
                    (90, PrismOff),
                ),
            )
        ],
        Motionstrip: [
            combo(
                for_bulbs(AnyColor),
                signal_switch(
                    randomize(
                        combo(Dimmer255, for_bulbs(Twinkle)),
                        combo(DimmersBeatChase, AllBulbs255),
                        combo(Dimmer255, for_bulbs(DimmersBeatChase)),
                        combo(Dimmer255, for_bulbs(StabPulse)),
                        combo(
                            Dimmer255,
                            for_bulbs(
                                with_args(
                                    "StabPulseHigh",
                                    StabPulse,
                                    signal=FrameSignal.freq_high,
                                )
                            ),
                        ),
                        combo(LightningStab, for_bulbs(LightningStab)),
                    ),
                ),
                randomize(MoveCircles, MoveFan),
            ),
        ],
        ChauvetColorBandPiX_36Ch: [
            combo(
                for_bulbs(AnyColor),
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
                        combo(
                            Dimmer255,
                            for_bulbs(
                                with_args(
                                    "GentlePulseHigh",
                                    GentlePulse,
                                    signal=FrameSignal.freq_high,
                                    trigger_level=0.2,
                                )
                            ),
                        ),
                        combo(Dimmer255, for_bulbs(DimmersBeatChase)),
                    ),
                ),
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
                for_bulbs(AnyColor),
                Spin,
                VerySlowDecay,
            ),
        ],
        ChauvetDerby: [
            combo(
                randomize(Spin, Noop),
                AnyColor,
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
    # Stroby: rave-like energy with only short / pulsy dimmer interpreters, plus
    # ``randomize(StrobeChannelSustained, Noop)`` so some partitions get strobed DMX.
    Mode.stroby: {
        (Group("sheer lights"), MovingHead): [
            combo(
                randomize(StrobeChannelSustained, Noop),
                weighted_randomize(
                    (
                        30,
                        combo(
                            AnyColor,
                            signal_switch(
                                randomize(
                                    HardSpatialPulse,
                                    HardSpatialCenterOutPulse,
                                    DimmersBeatChase,
                                    StabPulse,
                                    with_args(
                                        "StabPulseHigh",
                                        StabPulse,
                                        signal=FrameSignal.freq_high,
                                    ),
                                    LightningStab,
                                ),
                            ),
                            randomize(
                                MoveCircles,
                                MoveNod,
                                MoveFigureEight,
                                MoveFan,
                                MoveSmoothWalk,
                            ),
                            weighted_randomize(
                                (
                                    10,
                                    with_args(
                                        "StarburstGobo", MoverGobo, gobo="starburst"
                                    ),
                                ),
                                (90, MoverNoGobo),
                            ),
                            randomize(FocusBig, FocusSmall),
                            randomize(RotatePrism, PrismOff),
                        ),
                    ),
                    (70, Dimmer0),
                ),
            )
        ],
        Group("sheer lights"): [
            combo(randomize(StrobeChannelSustained, Noop), Dimmer0),
        ],
        Mirrorball: [
            combo(
                randomize(StrobeChannelSustained, Noop),
                weighted_randomize(
                    (10, combo(StabPulse, AnyColor)),
                    (90, Dimmer0),
                ),
            )
        ],
        Par: [
            combo(
                randomize(StrobeChannelSustained, Noop),
                AnyColor,
                signal_switch(
                    randomize(
                        StabPulse,
                        with_args(
                            "StabPulseHigh",
                            StabPulse,
                            signal=FrameSignal.freq_high,
                        ),
                        LightningStab,
                    ),
                ),
            )
        ],
        MovingHead: [
            combo(
                randomize(StrobeChannelSustained, Noop),
                AnyColor,
                signal_switch(
                    randomize(
                        HardSpatialPulse,
                        HardSpatialCenterOutPulse,
                        DimmersBeatChase,
                        StabPulse,
                        with_args(
                            "StabPulseHigh",
                            StabPulse,
                            signal=FrameSignal.freq_high,
                        ),
                        LightningStab,
                    ),
                ),
                randomize(
                    MoveCircles, MoveNod, MoveFigureEight, MoveFan, MoveSmoothWalk
                ),
                weighted_randomize(
                    (10, MoverRandomGobo),
                    (90, MoverNoGobo),
                ),
                weighted_randomize(
                    (10, FocusBig),
                    (90, FocusSmall),
                ),
                weighted_randomize(
                    (10, RotatePrism),
                    (90, PrismOff),
                ),
            )
        ],
        Motionstrip: [
            combo(
                randomize(StrobeChannelSustained, Noop),
                for_bulbs(AnyColor),
                signal_switch(
                    randomize(
                        combo(DimmersBeatChase, AllBulbs255),
                        combo(Dimmer255, for_bulbs(DimmersBeatChase)),
                        combo(Dimmer255, for_bulbs(StabPulse)),
                        combo(
                            Dimmer255,
                            for_bulbs(
                                with_args(
                                    "StabPulseHigh",
                                    StabPulse,
                                    signal=FrameSignal.freq_high,
                                )
                            ),
                        ),
                        combo(LightningStab, for_bulbs(LightningStab)),
                    ),
                ),
                randomize(MoveCircles, MoveFan),
            )
        ],
        ChauvetColorBandPiX_36Ch: [
            combo(
                randomize(StrobeChannelSustained, Noop),
                for_bulbs(AnyColor),
                signal_switch(
                    randomize(
                        combo(DimmersBeatChase, AllBulbs255),
                        combo(Dimmer255, for_bulbs(DimmersBeatChase)),
                        combo(Dimmer255, for_bulbs(StabPulse)),
                        combo(
                            Dimmer255,
                            for_bulbs(
                                with_args(
                                    "StabPulseHigh",
                                    StabPulse,
                                    signal=FrameSignal.freq_high,
                                )
                            ),
                        ),
                        combo(
                            Dimmer255,
                            for_bulbs(
                                with_args(
                                    "GentlePulseHigh",
                                    GentlePulse,
                                    signal=FrameSignal.freq_high,
                                    trigger_level=0.2,
                                )
                            ),
                        ),
                    ),
                ),
            )
        ],
        Laser: [
            combo(randomize(StrobeChannelSustained, Noop), signal_switch(LaserLatch)),
            combo(randomize(StrobeChannelSustained, Noop), StrobeHighSustained),
        ],
        ChauvetRotosphere_28Ch: [
            combo(
                randomize(StrobeChannelSustained, Noop),
                RotosphereSpinColor,
                randomize(
                    for_bulbs(StabPulse),
                    for_bulbs(GentlePulse),
                    LightningStab,
                ),
            ),
            combo(
                randomize(StrobeChannelSustained, Noop),
                for_bulbs(AnyColor),
                Spin,
                StabPulse,
            ),
        ],
        ChauvetDerby: [
            combo(
                randomize(StrobeChannelSustained, Noop),
                randomize(Spin, Noop),
                AnyColor,
                randomize(StabPulse, LightningStab, GentlePulse, Dimmer0),
            )
        ],
    },
    Mode.ethereal: {
        Mirrorball: [
            combo(
                Dimmer255,
                ColorAlternateBg,
            ),
        ],
        (Group("sheer lights"), MovingHead): [
            combo(
                with_args(
                    "EtherealSlowBreath",
                    SlowBreath,
                    period_seconds=14.0,
                    low=0.25,
                    high=0.85,
                ),
                ColorAlternateBg,
                # Circles multiplier is 5x slower than the previous 0.16 for a drifty feel.
                with_args("EtherealPhasedCircles", MoveCircles, multiplier=0.1),
                MoverRandomGobo,
                with_args("EtherealRotatePrism", RotatePrism, rotate_speed=0.2),
                with_args(
                    "EtherealRotatingGobo6",
                    RotatingGobo,
                    slot=6,
                    rotate_speed=0.3,
                ),
                FocusBig,
            )
        ],
        Group("sheer lights"): [combo(Dimmer255, ColorAlternateBg)],
    },
    Mode.test: {
        Mirrorball: [combo(Dimmer255, RigColorCycle)],
        Par: [combo(Dimmer255, RigColorCycle)],
        MovingHead: [
            combo(
                Dimmer255,
                RigColorCycle,
                PanTiltAxisCheck,
                MoverNoGobo,
                PrismOff,
                FocusSmall,
            )
        ],
        Motionstrip: [combo(Dimmer255, RigColorCycle)],
        ChauvetColorBandPiX_36Ch: [combo(Dimmer255, for_bulbs(RigColorCycle))],
        Laser: [combo(Dimmer255, RigColorCycle)],
        ChauvetRotosphere_28Ch: [combo(Dimmer255, RigColorCycle)],
        ChauvetDerby: [combo(Dimmer255, RigColorCycle)],
    },
}
