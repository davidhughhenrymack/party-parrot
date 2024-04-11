from parrot.fixtures.chauvet.mover_base import ChauvetSpot_12Ch
from parrot.utils.colour import Color
from ..base import ColorWheelEntry, GoboWheelEntry


# DMX layout:
dmx_layout = {
    "pan_coarse": 0,
    "pan_fine": 1,
    "tilt_coarse": 2,
    "tilt_fine": 3,
    "speed": 4,
    "color_wheel": 5,
    "shutter": 6,
    "dimmer": 7,
    "gobo_wheel": 8,
    "function": 9,
    "movement_macro": 10,
    "movement_macro_speed": 11,
}


color_wheel = [
    ColorWheelEntry(Color("white"), 0),
    ColorWheelEntry(Color("red"), 40),
    ColorWheelEntry(Color("green"), 70),
    ColorWheelEntry(Color("blue"), 100),
    ColorWheelEntry(Color("yellow"), 140),
    ColorWheelEntry(Color("magenta"), 170),
    ColorWheelEntry(Color("AntiqueWhite"), 200),
    ColorWheelEntry(Color("cyan"), 230),
]

gobo_wheel = [
    GoboWheelEntry("open", 0),
    GoboWheelEntry("wood", 40),
    GoboWheelEntry("spiral", 80),
    GoboWheelEntry("dots", 110),
    GoboWheelEntry("squares", 150),
    GoboWheelEntry("three", 180),
    GoboWheelEntry("circles", 200),
    GoboWheelEntry("ring", 255),
]


class ChauvetSpot120_12Ch(ChauvetSpot_12Ch):
    def __init__(
        self,
        patch,
        pan_lower=270,
        pan_upper=450,
        tilt_lower=0,
        tilt_upper=90,
        dimmer_upper=255,
    ):
        super().__init__(
            patch,
            "chauvet intimidator 120",
            12,
            dmx_layout,
            color_wheel,
            gobo_wheel,
            pan_lower,
            pan_upper,
            tilt_lower,
            tilt_upper,
            dimmer_upper,
        )
