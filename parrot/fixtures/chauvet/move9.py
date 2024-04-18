from parrot.fixtures.chauvet.mover_base import ChauvetMoverBase
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
    "gobo_wheel": 6,
    "dimmer": 7,
    "shutter": 8,
}


color_wheel = [
    ColorWheelEntry(Color("white"), 0),
    ColorWheelEntry(Color("red"), 10),
    ColorWheelEntry(Color("orange"), 16),
    ColorWheelEntry(Color("yellow"), 30),
    ColorWheelEntry(Color("blue"), 36),
    ColorWheelEntry(Color("AntiqueWhite"), 46),
    ColorWheelEntry(Color("cyan"), 53),
    ColorWheelEntry(Color("magenta"), 60),
    ColorWheelEntry(Color("green"), 63),
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


class ChauvetMove_9Ch(ChauvetMoverBase):
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
