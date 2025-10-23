import math
import time
from parrot.utils.colour import Color
from parrot.utils.color_extra import color_to_rgbw, dim_color
from parrot.utils.dmx_utils import Universe
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


class MotionstripBulb(FixtureBase):
    def __init__(self, address, universe=Universe.default):
        super().__init__(address, "motionstrip bulb", 4, universe)

    def render_values(self, values):
        c = color_to_rgbw(dim_color(self.get_color(), self.get_dimmer() / 255))
        for i in range(4):
            values[self.address + i] = c[i]


class Motionstrip(FixtureWithBulbs):
    pass


class Motionstrip38(Motionstrip):
    def __init__(
        self,
        patch,
        pan_lower=0,
        pan_upper=255,
        invert_pan=False,
        universe=Universe.default,
    ):
        super().__init__(
            patch,
            "motionstrip 38",
            38,
            [MotionstripBulb(6 + i * 4, universe) for i in range(8)],
            universe,
        )
        self.pan_lower = pan_lower
        self.pan_upper = pan_upper
        self.pan_range = pan_upper - pan_lower
        self.invert_pan = invert_pan
        self.set_pan_speed(128)
        self.set_strobe(0)

    def set_dimmer(self, value):
        FixtureBase.set_dimmer(self, value)
        self.values[4] = value

    def set_pan(self, value):
        if not self.invert_pan:
            self.values[0] = self.pan_lower + (self.pan_range * value / 255)
        else:
            self.values[0] = self.pan_lower + (self.pan_range * (255 - value) / 255)

    def set_pan_speed(self, value):
        self.values[1] = value

    def set_tilt(self, value):
        pass

    def set_strobe(self, value):
        super().set_strobe(value)

    def render(self, dmx):
        if self.get_strobe() > 0:
            self.values[4] = 255 * math.sin(time.time() * 30)
        super().render(dmx)
