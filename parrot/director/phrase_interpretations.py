from parrot.fixtures import LedPar
from parrot.fixtures.moving_head import MovingHead
from parrot.interpreters.base import (
    ColorAlternateBg,
    ColorBg,
    ColorFg,
    ColorRainbow,
    InterpreterBase,
    MoveCircles,
    MoveNod,
    Noop,
)
from parrot.director.phrase import Phrase
from parrot.interpreters.motionstrip import (
    MotionStripBulbBeatAndWiggle,
    MotionstripSlowRespond,
)
from parrot.interpreters.movers import (
    MoverBeatAndCircle,
    MoverBeatInFan,
    MoverDimAndCircle,
    MoverFan,
    MoverNoGobo,
    MoverRandomGobo,
)
from parrot.interpreters.rotosphere import RotosphereAll, RotosphereOn
from parrot.interpreters.slow import SlowDecay, SlowRespond
from parrot.fixtures.laser import Laser
from typing import List, Dict, Union
from parrot.fixtures.base import FixtureBase
from parrot.fixtures.motionstrip import Motionstrip
from parrot.interpreters.latched import DimmerFadeLatched, DimmerFadeLatchedRandom
from parrot.interpreters.dimmer import (
    DimmersBeatChase,
    GentlePulse,
    SequenceDimmers,
    SequenceFadeDimmers,
)
from parrot.interpreters.combo import combo

import random
from parrot.interpreters.dimmer import Dimmer0
from parrot.interpreters.randomize import randomize, weighted_randomize
from parrot.fixtures.chauvet.rotosphere import ChauvetRotosphere_28Ch


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
        Motionstrip: [MotionStripBulbBeatAndWiggle],
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
                randomize(GentlePulse, SlowRespond, DimmersBeatChase),
                randomize(ColorAlternateBg, ColorBg),
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
                    lambda group: DimmerFadeLatchedRandom(group, latch_at=0.3),
                ),
                weighted_randomize((95, ColorFg), (5, ColorRainbow)),
                randomize(MoveCircles, MoveNod),
                weighted_randomize((10, MoverRandomGobo), (90, MoverNoGobo)),
            )
        ],
        Motionstrip: [
            MotionstripSlowRespond,
            combo(
                randomize(SlowRespond, DimmersBeatChase, SlowDecay),
                randomize(ColorFg, ColorAlternateBg, ColorBg),
                MoveCircles,
            ),
            MotionStripBulbBeatAndWiggle,
        ],
        Laser: [DimmerFadeLatched],
        ChauvetRotosphere_28Ch: [RotosphereAll],
    },
}


def get_interpreter(
    phrase: Phrase, fixture_group: List[FixtureBase]
) -> Union[InterpreterBase]:
    for k, v in phrase_interpretations[phrase].items():
        if isinstance(fixture_group, list) and isinstance(fixture_group[0], k):
            c = random.choice(v)
            interp = c(fixture_group)
            return interp

    return Dimmer0(fixture_group)
