import enum
from parrot.fixtures import (
    ChauvetSpot160_12Ch,
    ChauvetSpot120_12Ch,
    ParRGB,
    Motionstrip38,
    FiveBeamLaser,
    TwoBeamLaser,
)
from parrot.fixtures.chauvet.rotosphere import ChauvetRotosphere_28Ch
from parrot.fixtures.chauvet.par import ChauvetParRGBWU
from parrot.fixtures.chauvet.derby import ChauvetDerby
from parrot.fixtures.chauvet.move9 import ChauvetMove_9Ch

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
        ChauvetRotosphere_28Ch(164),
    ],
    venues.mtn_lotus: [
        ParRGB(0),
        ParRGB(7),
        ParRGB(14),
        ParRGB(21),
        ParRGB(28),
        ParRGB(35),
        ParRGB(42),
        ParRGB(49),
        ChauvetSpot160_12Ch(56),
        ChauvetSpot120_12Ch(68),
        Motionstrip38(80, 0, 256),
        Motionstrip38(108, 0, 256),
        ChauvetParRGBWU(146),
        ChauvetParRGBWU(153),
        ChauvetDerby(160),
        ChauvetDerby(167),
        ChauvetMove_9Ch(174),
        ChauvetMove_9Ch(183),
    ],
}
