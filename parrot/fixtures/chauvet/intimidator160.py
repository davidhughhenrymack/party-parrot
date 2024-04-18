from parrot.utils.colour import Color
from parrot.fixtures.chauvet.mover_base import ChauvetMoverBase
from parrot.fixtures.base import GoboWheelEntry, ColorWheelEntry


# DMX layout:
dmx_layout = {
    "pan_coarse": 0,
    "pan_fine": 1,
    "tilt_coarse": 2,
    "tilt_fine": 3,
    "speed": 4,
    "color_wheel": 5,
    "gobo_wheel": 6,
    "dimmer": 7,
    "shutter": 8,
    "function": 9,
    "movement_macro": 10,
    "movement_macro_speed": 11,
}


color_wheel = [
    ColorWheelEntry(Color("white"), 0),
    ColorWheelEntry(Color("red"), 12),
    ColorWheelEntry(Color("orange"), 16),
    ColorWheelEntry(Color("yellow"), 22),
    ColorWheelEntry(Color("green"), 30),
    ColorWheelEntry(Color("blue"), 37),
    ColorWheelEntry(Color("AntiqueWhite"), 46),
    ColorWheelEntry(Color("cyan"), 52),
    ColorWheelEntry(Color("magenta"), 58),
    ColorWheelEntry(Color("lime"), 64),
]

gobo_wheel = [
    GoboWheelEntry("open", 0),
    GoboWheelEntry("dots", 9),
    GoboWheelEntry("spiral", 14),
    GoboWheelEntry("spiral2", 20),
    GoboWheelEntry("starburst", 26),
    GoboWheelEntry("four", 32),
    GoboWheelEntry("waves", 38),
    GoboWheelEntry("biohazard", 45),
    GoboWheelEntry("ring", 50),
    GoboWheelEntry("flower", 60),
]


class ChauvetSpot160_12Ch(ChauvetMoverBase):
    def __init__(
        self,
        patch,
        pan_lower=360,
        pan_upper=360 + 180,
        tilt_lower=0,
        tilt_upper=90,
        dimmer_upper=255,
    ):
        super().__init__(
            patch,
            "chauvet intimidator 160",
            11,
            dmx_layout,
            color_wheel,
            gobo_wheel,
            pan_lower,
            pan_upper,
            tilt_lower,
            tilt_upper,
            dimmer_upper,
        )
