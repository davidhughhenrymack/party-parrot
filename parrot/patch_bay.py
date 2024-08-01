import enum
from parrot.fixtures import (
    ChauvetSpot160_12Ch,
    ChauvetSpot120_12Ch,
    ParRGB,
    Motionstrip38,
    FiveBeamLaser,
    TwoBeamLaser,
)
from parrot.fixtures.chauvet.gigbar import ChauvetGigBarMoveILS
from parrot.fixtures.chauvet.rotosphere import ChauvetRotosphere_28Ch
from parrot.fixtures.chauvet.par import ChauvetParRGBAWU
from parrot.fixtures.chauvet.derby import ChauvetDerby
from parrot.fixtures.chauvet.move9 import ChauvetMove_9Ch
from parrot.fixtures.led_par import ParRGBAWU

venues = enum.Enum("Venues", ["dmack", "mtn_lotus"])

venue_patches = {
    venues.dmack: [
        ChauvetSpot160_12Ch(
            patch=1,
        ),
        ChauvetSpot120_12Ch(
            patch=140,
        ),
        ParRGB(12),
        ParRGB(19),
        ParRGB(26),
        ParRGB(33),
        ParRGB(40),
        ParRGB(47),
        Motionstrip38(59, 0, 256),
        Motionstrip38(154, 0, 256),
        FiveBeamLaser(100),
        TwoBeamLaser(120),
        # ChauvetRotosphere_28Ch(164),
    ],
    venues.mtn_lotus: [
        *[ParRGBAWU(i) for i in range(10, 90, 10)],
        # ChauvetSpot160_12Ch(56),
        # ChauvetSpot120_12Ch(68),
        # Motionstrip38(80, 0, 256),
        # Motionstrip38(108, 0, 256),
        # GigbarMove ILS 50 channel
        *ChauvetGigBarMoveILS(100),
        TwoBeamLaser(150),
        ChauvetSpot120_12Ch(160),
        ChauvetSpot160_12Ch(172),
    ],
}
