from parrot.fixtures.chauvet import ChauvetSpot160
from parrot.fixtures.led_par import LedPar
from parrot.fixtures.motionstrip import Motionstrip38
from parrot.fixtures.uking.laser import FiveBeamLaser
from parrot.fixtures.oultia.laser import TwoBeamLaser


patch_bay = [
    ChauvetSpot160(1, 90, 270, 20, 100, 40),
    LedPar(12),
    LedPar(19),
    LedPar(26),
    LedPar(33),
    Motionstrip38(59, 0, 128),
    FiveBeamLaser(100),
    TwoBeamLaser(120),
]
