from parrot.fixtures import LedPar
from parrot.fixtures.moving_head import MovingHead
from parrot.interpreters.base import InterpreterBase, Phrase, ColorFg
from parrot.interpreters.motionstrip import (
    MotionStripBulbBeatAndWiggle,
    MotionstripSlowRespond,
)
from parrot.interpreters.movers import (
    MoverBeatAndCircle,
    MoverDimAndCircle,
    MoverBeatInFan,
    MoverSequenceAndCircle,
    MoverSequenceInFan,
)
from parrot.interpreters.slow import SlowDecay, SlowRespond
from parrot.fixtures.laser import Laser
from typing import List, Dict, Union
from parrot.fixtures.base import FixtureBase
from parrot.fixtures.motionstrip import Motionstrip
from parrot.interpreters.latched import DimmerFadeLatched
from parrot.interpreters.dimmer import Dimmer100, Dimmer30
from parrot.interpreters.combo import comboify

import random
from parrot.interpreters.dimmer import Dimmer0


phrase_interpretations: Dict[
    Phrase,
    Dict[FixtureBase, List[InterpreterBase]],
] = {
    Phrase.intro_outro: {
        LedPar: [SlowDecay, SlowRespond],
    },
    Phrase.build: {
        # LEDs off
        # Moving heads flashing beat, (drawing circles / fixed position)
        # Motion strip off or bulb flashing to the beat
        MovingHead: [MoverBeatAndCircle, MoverBeatInFan],
        Motionstrip: [MotionStripBulbBeatAndWiggle],
    },
    Phrase.drop: {
        # LEDs pulsing vividly
        # Moving sequencing on, drawing circles. maybe strobing
        # Motion strip swishing
        # lasers on during intense moments
        LedPar: [SlowDecay],
        MovingHead: [MoverSequenceAndCircle, MoverSequenceInFan],
        Motionstrip: [MotionstripSlowRespond],
        Laser: [DimmerFadeLatched],
    },
    Phrase.breakdown: {
        # Leds pulsing gently
        # Movers slowly moving, on low dimmer, drawing circles
        # Motion strip slowly moving and pulsing along bulbs
        LedPar: [SlowDecay],
        MovingHead: [MoverDimAndCircle],
        Motionstrip: [MotionstripSlowRespond],
    },
    Phrase.test: {
        LedPar: [comboify([Dimmer30, ColorFg])],
        MovingHead: [MoverDimAndCircle],
        Motionstrip: [MoverDimAndCircle],
        Laser: [Dimmer100],
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
