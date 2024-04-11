from parrot.utils.colour import Color
from parrot.utils.color_extra import dim_color
from .base import FixtureBase, FixtureWithBulbs

# DMX layout:
dmx_layout = [
    "pan",
    "pan_speed",
    ["built_in_program", 0],
    "built_in_program_speed",
    "master_dimmer",
    "strobe" "bulb 1: RGBW",
    "bulb 2: RGBW",
    "bulb 3: RGBW",
    "bulb 4: RGBW",
    "bulb 5: RGBW",
    "bulb 6: RGBW",
    "bulb 7: RGBW",
    "bulb 8: RGBW",
]


def color_to_rgbw(color: Color):
    if color.get_saturation() < 0.1:
        return (0, 0, 0, color.luminance * 255)
    else:
        return (color.red * 255, color.green * 255, color.blue * 255, 0)


class MotionstripBulb(FixtureBase):
    def __init__(self, address):
        super().__init__(address, "motionstrip bulb", 4)

    def render_values(self, values):
        c = color_to_rgbw(dim_color(self.get_color(), self.get_dimmer() / 255))
        for i in range(4):
            values[self.address + i] = c[i]


class Motionstrip(FixtureWithBulbs):
    pass


class Motionstrip38(Motionstrip):
    def __init__(self, patch, pan_lower, pan_upper):
        super().__init__(
            patch, "motionstrip 38", 38, [MotionstripBulb(6 + i * 4) for i in range(8)]
        )
        self.pan_lower = pan_lower
        self.pan_upper = pan_upper
        self.pan_range = pan_upper - pan_lower
        self.set_pan_speed(128)

    def set_dimmer(self, value):
        FixtureBase.set_dimmer(self, value)
        self.values[4] = value

    def set_pan(self, value):
        self.values[0] = self.pan_lower + (self.pan_range * value / 255)

    def set_pan_speed(self, value):
        self.values[1] = value

    def set_tilt(self, value):
        pass
