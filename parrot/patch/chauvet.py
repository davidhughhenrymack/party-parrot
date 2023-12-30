from parrot.utils.colour import Color
from .base import FixtureBase


# DMX layout:
dmx_layout = [
    "pan 0 -540",
    "fine pan",
    "tilt 0 - 229",
    "fine tilt",
    "pan/tilt speed",
    "color wheel",
    "gobo wheel",
    "dimmer",
    "shutter",
    "control function",
    "movement macro",
]


class ColorWheelEntry:
    def __init__(self, color: Color, dmx_value: int):
        self.color = color
        self.dmx_value = dmx_value


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


class ChauvetSpot160(FixtureBase):
    def __init__(
        self, patch, pan_lower, pan_upper, tilt_lower, tilt_upper, dimmer_upper=255
    ):
        super().__init__(patch, "chauvet intimidator 160", 11)
        self.pan_lower = pan_lower / 540 * 255
        self.pan_upper = pan_upper / 540 * 255
        self.pan_range = self.pan_upper - self.pan_lower
        self.tilt_lower = tilt_lower / 229 * 255
        self.tilt_upper = tilt_upper / 229 * 255
        self.tilt_range = self.tilt_upper - self.tilt_lower
        self.dimmer_upper = dimmer_upper

        self.set_speed(0)
        self.set_shutter_open()

    def set_dimmer(self, value):
        self.values[7] = value / 255 * self.dimmer_upper

    # 0 - 255
    def set_pan(self, value):
        projected = self.pan_lower + (self.pan_range * value / 255)
        self.values[0] = int(projected)
        self.values[1] = int((projected - self.values[0]) * 255)

    # 0 - 255
    def set_tilt(self, value):
        projected = self.tilt_lower + (self.tilt_range * value / 255)
        self.values[2] = int(projected)
        self.values[3] = int((projected - self.values[2]) * 255)

    def set_speed(self, value):
        self.values[4] = value

    def set_color(self, color: Color):
        super().set_color(color)
        # Find the closest color in the color wheel
        closest = None
        for entry in color_wheel:
            if closest == None or abs(entry.color.hue - color.hue) < abs(
                closest.color.hue - color.hue
            ):
                closest = entry

        # Set the color wheel value
        self.values[5] = closest.dmx_value

    def set_strobe(self, value):
        lower = 4
        upper = 76
        scaled = lower + (upper - lower) * value / 255
        self.values[8] = scaled

    def set_shutter_open(self):
        self.values[8] = 6
