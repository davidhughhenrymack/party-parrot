from parrot.fixtures import LedPar
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
    with_args,
)
from parrot.director.phrase import Phrase
from parrot.interpreters.motionstrip import (
    MotionstripSlowRespond,
)
from parrot.interpreters.movers import (
    MoverBeatAndCircle,
    MoverBeatInFan,
    MoverDimAndCircle,
    MoverGobo,
    MoverNoGobo,
)
from parrot.interpreters.rotosphere import (
    RotosphereOn,
    RotosphereSpin,
    RotosphereSpinColor,
)
from parrot.interpreters.slow import (
    MellowOnly,
    SlowDecay,
    SlowRespond,
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
from parrot.director.phrase_interpretations import with_args
from parrot.interpreters.laser import LaserLatch
from parrot.interpreters.strobe import StrobeHighSustained


phrase_interpretations: Dict[
    Phrase,
    Dict[FixtureBase, List[InterpreterBase]],
] = {
    Phrase.intro_outro: {
        LedPar: [
            combo(SlowDecay, ColorAlternateBg),
            combo(SlowRespond, ColorAlternateBg),
        ],
        ChauvetRotosphere_28Ch: [RotosphereOn],
    },
    Phrase.build: {
        # LEDs off
        # Moving heads flashing beat, (drawing circles / fixed position)
        # Motion strip off or bulb flashing to the beat
        MovingHead: [MoverBeatAndCircle, MoverBeatInFan],
        Motionstrip: [],
        LedPar: [combo(DimmersBeatChase, ColorAlternateBg)],
    },
    Phrase.drop: {
        # LEDs pulsing vividly
        # Moving sequencing on, drawing circles. maybe strobing
        # Motion strip swishing
        # lasers on during intense moments
        LedPar: [combo(SlowDecay, ColorAlternateBg)],
        MovingHead: [combo(DimmersBeatChase, ColorFg, MoveCircles)],
        Motionstrip: [MotionstripSlowRespond],
        Laser: [DimmerFadeLatched],
    },
    Phrase.breakdown: {
        # Leds pulsing gently
        # Movers slowly moving, on low dimmer, drawing circles
        # Motion strip slowly moving and pulsing along bulbs
        LedPar: [combo(GentlePulse, ColorAlternateBg)],
        MovingHead: [MoverDimAndCircle],
        Motionstrip: [combo(SlowRespond, ColorFg, MoveCircles)],
    },
    Phrase.general: {
        LedPar: [
            combo(
                randomize(
                    GentlePulse,
                    SlowRespond,
                    DimmersBeatChase,
                    VerySlowDecay,
                    StrobeHighSustained,
                    SlowSustained,
                ),
                randomize(ColorAlternateBg, ColorBg, ColorRainbow),
            ),
        ],
        MovingHead: [
            combo(
                randomize(
                    DimmersBeatChase,
                    SlowDecay,
                    GentlePulse,
                    DimmerFadeLatched,
                    SequenceDimmers,
                    SequenceFadeDimmers,
                    MellowOnly,
                    with_args(DimmerFadeLatchedRandom, latch_at=0.3),
                ),
                weighted_randomize((95, ColorFg), (5, ColorRainbow)),
                randomize(MoveCircles, MoveNod),
                weighted_randomize(
                    (10, with_args(MoverGobo, gobo="starburst")), (90, MoverNoGobo)
                ),
            )
        ],
        Motionstrip: [
            # MotionstripSlowRespond,
            combo(
                randomize(
                    combo(Dimmer255, for_bulbs(Twinkle)),
                    combo(SlowRespond, AllBulbs255),
                    combo(DimmersBeatChase, AllBulbs255),
                    combo(SlowDecay, AllBulbs255),
                    combo(
                        Dimmer255,
                        for_bulbs(with_args(GentlePulse, trigger_level=0.1)),
                    ),
                    combo(Dimmer255, for_bulbs(DimmersBeatChase)),
                    combo(Dimmer255, for_bulbs(SequenceFadeDimmers)),
                ),
                randomize(ColorFg, ColorAlternateBg, ColorBg, for_bulbs(ColorRainbow)),
                MoveCircles,
            ),
        ],
        Laser: [LaserLatch],
        ChauvetRotosphere_28Ch: [
            Dimmer0,
            combo(
                RotosphereSpinColor,
                randomize(
                    DimmerFadeIn,
                    for_bulbs(Twinkle),
                    for_bulbs(GentlePulse),
                    DimmerFadeLatched4s,
                    SlowSustained,
                    MellowOnly,
                ),
            ),
            combo(
                for_bulbs(ColorRainbow),
                RotosphereSpin,
                with_args(SlowDecay, decay_rate=0.01),
            ),
        ],
    },
}


def get_interpreter(
    phrase: Phrase, fixture_group: List[FixtureBase], args: InterpreterArgs
) -> Union[InterpreterBase]:
    for k, v in phrase_interpretations[phrase].items():
        if isinstance(fixture_group, list) and isinstance(fixture_group[0], k):
            c = randomize(*v)
            interp = c(fixture_group, args)
            return interp

    return Dimmer0(fixture_group, args)
