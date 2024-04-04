from parrot.fixtures import (
    ChauvetSpot160_12Ch,
    ChauvetSpot120_12Ch,
    LedPar,
    Motionstrip38,
    FiveBeamLaser,
    TwoBeamLaser,
)

patch_bay = [
    ChauvetSpot160_12Ch(
        patch=1,
    ),
    ChauvetSpot120_12Ch(
        patch=140,
    ),
    ChauvetSpot120_12Ch(
        patch=152,
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
]
