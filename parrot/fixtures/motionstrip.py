import math
import time
from parrot.utils.colour import Color
from parrot.utils.color_extra import color_to_rgbw, dim_color
from parrot.utils.dmx_utils import Universe
from .base import FixtureBase, FixtureWithBulbs

# DMX layout reference for Motionstrip38's 38-channel mode.
# Purely documentation — the runtime code uses fixed numeric indices
# (see set_pan/set_pan_speed/set_dimmer/render below and the bulb 4-channel
# stride starting at offset 6 configured in Motionstrip38.__init__).
dmx_layout = [
    "pan",                          # 0
    "pan_speed",                    # 1
    "built_in_program",             # 2
    "built_in_program_speed",       # 3
    "master_dimmer",                # 4
    "strobe",                       # 5
    "bulb 1: RGBW",                 # 6  (+ 4 per bulb)
    "bulb 2: RGBW",                 # 10
    "bulb 3: RGBW",                 # 14
    "bulb 4: RGBW",                 # 18
    "bulb 5: RGBW",                 # 22
    "bulb 6: RGBW",                 # 26
    "bulb 7: RGBW",                 # 30
    "bulb 8: RGBW",                 # 34
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
        # 0-5 = strobe off
        # 6-255 = strobe speed
        # Even speed 255 is pretty slow, so we render our own strobe in the dimmer
        # self.values[5] = super().get_strobe()

    def render(self, dmx):
        if self.get_strobe() > 0:
            self.values[4] = 255 * math.sin(time.time() * 30)
        super().render(dmx)
