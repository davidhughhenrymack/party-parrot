from parrot.fixtures.chauvet.colorband_pix import ChauvetColorBandPiX_36Ch
from parrot.fixtures.moving_head import MovingHead
from parrot.interpreters.base import (
    ColorAlternateBg,
    ColorBg,
    ColorFg,
    ColorRainbow,
    InterpreterArgs,
    InterpreterBase,
    MoveCircles,
    MoveNod,
    Noop,
    with_args,
)
from parrot.director.mode import Mode
from parrot.interpreters.motionstrip import PanLatched
from parrot.interpreters.movers import (
    MoverGobo,
    MoverNoGobo,
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
from typing import List, Dict, Union
from parrot.fixtures.base import FixtureBase
from parrot.fixtures.motionstrip import Motionstrip
from parrot.interpreters.latched import (
    DimmerFadeLatched,
    DimmerFadeLatched4s,
    DimmerFadeLatchedRandom,
)
from parrot.interpreters.dimmer import (
    Dimmer255,
    DimmerFadeIn,
    DimmersBeatChase,
    GentlePulse,
    SequenceDimmers,
    SequenceFadeDimmers,
    Twinkle,
)
from parrot.interpreters.combo import combo

from parrot.interpreters.dimmer import Dimmer0
from parrot.interpreters.randomize import randomize, weighted_randomize
from parrot.fixtures.chauvet.rotosphere import ChauvetRotosphere_28Ch
from parrot.interpreters.bulbs import AllBulbs255, for_bulbs
from parrot.director.mode_interpretations import with_args
from parrot.interpreters.laser import LaserLatch
from parrot.interpreters.strobe import StrobeHighSustained
from parrot.interpreters.signal import signal_switch
from parrot.fixtures.led_par import Par
from parrot.fixtures.chauvet.derby import ChauvetDerby


mode_interpretations: Dict[
    Mode,
    Dict[FixtureBase, List[InterpreterBase]],
] = {
    Mode.blackout: {},
    Mode.gentle: {
        Par: [combo(signal_switch(randomize(GentlePulse, Twinkle)), ColorBg)],
        MovingHead: [
            combo(signal_switch(randomize(GentlePulse, Twinkle)), ColorBg, MoveCircles)
        ],
        Motionstrip: [combo(signal_switch(randomize(GentlePulse, Twinkle)), ColorBg)],
        ChauvetColorBandPiX_36Ch: [
            combo(signal_switch(randomize(GentlePulse, Twinkle)), ColorBg)
        ],
        Laser: [signal_switch(Dimmer0)],
        ChauvetRotosphere_28Ch: [
            combo(signal_switch(randomize(GentlePulse, Twinkle)), ColorBg)
        ],
        ChauvetDerby: [combo(signal_switch(randomize(GentlePulse, Twinkle)), ColorBg)],
    },
    Mode.rave: {
        Par: [
            combo(
                signal_switch(
                    randomize(
                        DimmersBeatChase,
                        SequenceFadeDimmers,
                        GentlePulse,
                        VerySlowDecay,
                        SlowSustained,
                    ),
                ),
                randomize(ColorAlternateBg, ColorBg, ColorRainbow),
            ),
        ],
        MovingHead: [
            combo(
                signal_switch(
                    randomize(
                        DimmersBeatChase,
                        SlowDecay,
                        GentlePulse,
                        DimmerFadeLatched,
                        SequenceDimmers,
                        SequenceFadeDimmers,
                        with_args(
                            "FadeLatchAt0.3", DimmerFadeLatchedRandom, latch_at=0.3
                        ),
                    ),
                ),
                weighted_randomize((95, ColorFg), (5, ColorRainbow)),
                randomize(MoveCircles, MoveNod),
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
                randomize(PanLatched, MoveCircles),
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
}


def get_interpreter(
    phrase: Mode, fixture_group: List[FixtureBase], args: InterpreterArgs
) -> Union[InterpreterBase]:
    for k, v in mode_interpretations[phrase].items():
        if isinstance(fixture_group, list) and isinstance(fixture_group[0], k):
            c = randomize(*v)
            interp = c(fixture_group, args)
            return interp

    return Dimmer0(fixture_group, args)
