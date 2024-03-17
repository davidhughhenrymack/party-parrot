from parrot.utils.colour import Color
from .base import FixtureBase

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


class Motionstrip(FixtureBase):
    def __init__(self, address, name, width):
        super().__init__(address, name, width)


class Motionstrip38(Motionstrip):
    def __init__(self, patch, pan_lower, pan_upper):
        super().__init__(patch, "motionstrip 38", 38)
        self.pan_lower = pan_lower
        self.pan_upper = pan_upper
        self.pan_range = pan_upper - pan_lower
        self.set_pan_speed(128)

    def set_dimmer(self, value):
        super().set_dimmer(value)
        self.values[4] = value

    def set_pan(self, value):
        self.values[0] = self.pan_lower + (self.pan_range * value / 255)

    def set_pan_speed(self, value):
        self.values[1] = value

    def set_color(self, color: Color):
        super().set_color(color)
        for i in range(8):
            c = color_to_rgbw(color)
            for j in range(4):
                self.values[6 + j + (i * 4)] = c[j]

    def set_bulb_color(self, bulb: int, color: Color):
        if bulb < 0 or bulb > 7:
            raise ValueError("bulb must be between 0 and 7")

        c = color_to_rgbw(color)
        for i in range(4):
            self.values[6 + bulb * 4 + i] = c[i]
