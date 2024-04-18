from parrot.fixtures.base import FixtureBase
from parrot.utils.color_extra import render_color_components
from parrot.utils.colour import Color
from parrot.utils.math import clamp
from parrot.fixtures.led_par import Par


class ChauvetParRGBWU(Par):
    def __init__(self, address):
        super().__init__(address, "chauvet par rgbwu", 7)

    def set_color(self, color):
        super().set_color(color)
        render_color_components(
            [
                Color("red"),
                Color("green"),
                Color("blue"),
                Color("white"),
                Color("purple"),
            ],
            color,
            self.get_dimmer(),
            self.values,
            0,
        )

    def set_strobe(self, value):
        super().set_strobe(value)
        self.values[6] = clamp(value, 0, 250)
