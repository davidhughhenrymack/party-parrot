"""Mode → (fixture matcher → interpreter options) expression.

This file is intentionally just the DSL data. The matching/dispatch machinery
(how a matcher resolves, how a ``Mode`` plus a fixture group becomes an
``InterpreterBase``) lives in :mod:`parrot.director.mode_dispatch`.
"""

from __future__ import annotations

from typing import Dict, List

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
    ColorAlternateBg,
    ColorBg,
    ColorFg,
    ColorRainbow,
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
    MoveCircleSync,
    MoveCircles,
    MoveCirclesPhased,
    MoveFan,
    MoveFigureEight,
    MoveNod,
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
from parrot.interpreters.strobe import StrobeHighSustained


mode_interpretations: Dict[Mode, Dict[Matcher, List[InterpreterBase]]] = {
    Mode.blackout: {},
    Mode.chill: {
        # Sheer lights are an ethereal-mode-only feature; keep them dark elsewhere.
        Group("sheer lights"): [Dimmer0],
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
        Motionstrip: [Dimmer0],
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
        Group("sheer lights"): [Dimmer0],
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
                        signal_switch(
                            randomize(
                                HardSpatialPulse,
                                HardSpatialCenterOutPulse,
                                DimmersBeatChase,
                                GentlePulse,
                                DimmerFadeLatched,
                                SequenceDimmers,
                                SequenceFadeDimmers,
                                StabPulse,
                                LightningStab,
                            ),
                        ),
                        weighted_randomize(
                            (70, ColorFg), (25, ColorAlternateBg), (5, ColorRainbow)
                        ),
                        randomize(MoveCircles, MoveNod, MoveFigureEight, MoveFan),
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
                weighted_randomize(
                    (70, ColorFg), (25, ColorAlternateBg), (5, ColorRainbow)
                ),
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
            combo(
                with_args("MirrorballFade10s", DimmerFadeInLinearSeconds, seconds=10.0),
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
                with_args("EtherealPhasedCircles", MoveCirclesPhased, multiplier=0.1),
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
