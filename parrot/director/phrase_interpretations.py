from parrot.fixtures import LedPar
from parrot.fixtures.moving_head import MovingHead
from parrot.interpreters.base import (
    GroupInterpreterBase,
    InterpreterBase,
    Phrase,
)
from parrot.interpreters.motionstrip import (
    MotionStripBulbBeatAndWiggle,
    MotionstripSlowRespond,
)
from parrot.interpreters.movers import (
    MoverBeatAndCircle,
    MoverDimAndCircle,
    MoverGroupBeatInFan,
    MoverSequenceAndCircle,
    MoverSequenceInFan,
)
from parrot.interpreters.slow import GroupSlowDecay, GroupSlowRespond
from parrot.fixtures.laser import Laser
from typing import List, Dict, Union
from parrot.fixtures.base import FixtureBase
from parrot.fixtures.motionstrip import Motionstrip
from parrot.interpreters.latched import DimmerFadeLatched


phrase_interpretations: Dict[
    Phrase,
    Dict[FixtureBase, List[Union[GroupInterpreterBase, InterpreterBase]]],
] = {
    Phrase.intro_outro: {
        LedPar: [GroupSlowDecay, GroupSlowRespond],
    },
    Phrase.build: {
        # LEDs off
        # Moving heads flashing beat, (drawing circles / fixed position)
        # Motion strip off or bulb flashing to the beat
        MovingHead: [MoverBeatAndCircle, MoverGroupBeatInFan],
        Motionstrip: [MotionStripBulbBeatAndWiggle],
    },
    Phrase.drop: {
        # LEDs pulsing vividly
        # Moving sequencing on, drawing circles. maybe strobing
        # Motion strip swishing
        # lasers on during intense moments
        LedPar: [GroupSlowDecay],
        MovingHead: [MoverSequenceAndCircle, MoverSequenceInFan],
        Motionstrip: [MotionstripSlowRespond],
        Laser: [DimmerFadeLatched],
    },
    Phrase.breakdown: {
        # Leds pulsing gently
        # Movers slowly moving, on low dimmer, drawing circles
        # Motion strip slowly moving and pulsing along bulbs
        LedPar: [GroupSlowDecay],
        MovingHead: [MoverDimAndCircle],
        Motionstrip: [MotionstripSlowRespond],
    },
}
