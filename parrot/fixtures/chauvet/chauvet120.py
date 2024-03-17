from parrot.utils.colour import Color
from parrot.utils.color_extra import color_distance
from ..base import FixtureBase, ColorWheelEntry, GoboWheelEntry


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


class ChauvetSpot120_12Ch(FixtureBase):
    def __init__(
        self,
        patch,
        pan_lower=270,
        pan_upper=450,
        tilt_lower=0,
        tilt_upper=90,
        dimmer_upper=255,
    ):
        super().__init__(patch, "chauvet intimidator 120", 11)
        self.pan_lower = pan_lower / 540 * 255
        self.pan_upper = pan_upper / 540 * 255
        self.pan_range = self.pan_upper - self.pan_lower
        self.tilt_lower = tilt_lower / 229 * 255
        self.tilt_upper = tilt_upper / 229 * 255
        self.tilt_range = self.tilt_upper - self.tilt_lower
        self.dimmer_upper = dimmer_upper

        self.set_speed(0)
        self.set_shutter_open()

    def set(self, name, value):
        if name in dmx_layout:
            self.values[dmx_layout[name]] = value

    def set_dimmer(self, value):
        self.set("dimmer", value / 255 * self.dimmer_upper)

    # 0 - 255
    def set_pan(self, value):
        projected = self.pan_lower + (self.pan_range * value / 255)
        self.set("pan_coarse", int(projected))
        self.set("pan_fine", int((projected - self.values[0]) * 255))

    # 0 - 255
    def set_tilt(self, value):
        projected = self.tilt_lower + (self.tilt_range * value / 255)
        self.set("tilt_coarse", int(projected))
        self.set("tilt_fine", int((projected - self.values[2]) * 255))

    def set_speed(self, value):
        self.set("speed", value)

    def set_color(self, color: Color):
        super().set_color(color)
        # Find the closest color in the color wheel
        closest = None
        for entry in color_wheel:
            if closest == None or color_distance(entry.color, color) < color_distance(
                closest.color, color
            ):
                closest = entry

        # Set the color wheel value
        self.set("color_wheel", closest.dmx_value)

    def set_strobe(self, value):
        lower = 4
        upper = 76
        scaled = lower + (upper - lower) * value / 255
        self.set("shutter", scaled)

    def set_shutter_open(self):
        self.set("shutter", 6)
