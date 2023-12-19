from patch.led_par import LedPar
from patch.motionstrip import Motionstrip38

patch_bay = [
    LedPar(19),
    LedPar(12),
    LedPar(26),
    Motionstrip38(59, 0, 128)
]