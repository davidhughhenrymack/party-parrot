from patch.led_par import LedPar
from patch.motionstrip import Motionstrip38
from patch.chauvet import ChauvetSpot160

patch_bay = [
    ChauvetSpot160(1, 90, 270, 20, 100, 40),
    LedPar(19),
    LedPar(12),
    LedPar(26),
    LedPar(33),
    Motionstrip38(59, 0, 128)
]