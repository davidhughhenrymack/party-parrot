from parrot.fixtures.chauvet import ChauvetSpot160
from parrot.fixtures.led_par import LedPar
from parrot.fixtures.motionstrip import Motionstrip38
from parrot.fixtures.uking.laser import FiveBeamLaser
from parrot.fixtures.oultia.laser import TwoBeamLaser


patch_bay = [
    ChauvetSpot160(
        patch=1,
        pan_lower=180 + 90,
        pan_upper=180 + 90 + 180,
        tilt_lower=0,
        tilt_upper=90,
        dimmer_upper=255,
    ),
    LedPar(12),
    LedPar(19),
    LedPar(26),
    LedPar(33),
    Motionstrip38(59, 128, 256),
    FiveBeamLaser(100),
    TwoBeamLaser(120),
]
