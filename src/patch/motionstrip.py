
from utils.colour import Color
from utils.colour import RGB
from .base import BaseFixture

# DMX layout:
dmx_layout = [
    "pan",
    "pan_speed",
    ["built_in_program", 0],
    "built_in_program_speed",
    "master_dimmer",
    "strobe"
    "bulb 1: RGBW",
    "bulb 2: RGBW",
    "bulb 3: RGBW",
    "bulb 4: RGBW",
    "bulb 5: RGBW",
    "bulb 6: RGBW",
    "bulb 7: RGBW",
    "bulb 8: RGBW",
]

class Motionstrip38(BaseFixture):
    def __init__(self, patch, pan_lower, pan_upper):
        super().__init__(patch, "motionstrip 38", 38)
        self.pan_lower = pan_lower
        self.pan_upper = pan_upper
        self.pan_range = pan_upper - pan_lower
        self.set_pan_speed(128)

    def set_dimmer(self, value):
        self.values[4] = value

    def set_pan(self, value):
        self.values[0] = self.pan_lower + (self.pan_range * value / 255)

    def set_pan_speed(self, value):
        self.values[1] = value

    def set_color(self, color: Color):
        for i in range(8):
            if color == Color('white'):
                self.values[6 + i * 4] = 0
                self.values[7 + i * 4] = 0
                self.values[8 + i * 4] = 0
                self.values[9 + i * 4] = 255
            else:
                self.values[6 + i * 4] = color.red * 255
                self.values[7 + i * 4] = color.green * 255
                self.values[8 + i * 4] = color.blue * 255
                self.values[9 + i * 4] = 0