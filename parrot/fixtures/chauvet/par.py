from parrot.fixtures.base import FixtureBase
from parrot.utils.color_extra import color_to_rgbw, render_color_components
from parrot.utils.colour import Color
from parrot.utils.math import clamp
from parrot.fixtures.led_par import Par


class ChauvetParRGBAWU(Par):
    def __init__(self, address):
        super().__init__(address, "chauvet par rgbwu", 7)

    def set_color(self, color):
        super().set_color(color)
        (r, g, b, w) = color_to_rgbw(color)
        self.values[0] = r
        self.values[1] = g
        self.values[2] = b
        self.values[4] = w
        self.values[5] = b

    def set_strobe(self, value):
        super().set_strobe(value)
        # Use accumulated strobe_value for DMX output
        self.values[6] = clamp(self.strobe_value, 0, 250)
