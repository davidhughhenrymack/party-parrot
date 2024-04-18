import enum
from parrot.fixtures import (
    ChauvetSpot160_12Ch,
    ChauvetSpot120_12Ch,
    LedPar,
    Motionstrip38,
    FiveBeamLaser,
    TwoBeamLaser,
)
from parrot.fixtures.chauvet.rotosphere import ChauvetRotosphere_28Ch

venues = enum.Enum("Venues", ["dmack", "mtn_lotus"])

venue_patches = {
    venues.dmack: [
        ChauvetSpot160_12Ch(
            patch=1,
        ),
        ChauvetSpot120_12Ch(
            patch=140,
        ),
        LedPar(12),
        LedPar(19),
        LedPar(26),
        LedPar(33),
        LedPar(40),
        LedPar(47),
        Motionstrip38(59, 0, 256),
        Motionstrip38(154, 0, 256),
        FiveBeamLaser(100),
        TwoBeamLaser(120),
        ChauvetRotosphere_28Ch(164),
    ],
    venues.mtn_lotus: [
        LedPar(0),
        LedPar(7),
        LedPar(14),
        LedPar(21),
        LedPar(28),
        LedPar(35),
        LedPar(42),
        LedPar(49),
        ChauvetSpot160_12Ch(56),
        ChauvetSpot120_12Ch(68),
        Motionstrip38(80, 0, 256),
        Motionstrip38(108, 0, 256),
    ],
}
