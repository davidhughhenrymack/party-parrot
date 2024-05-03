from parrot.utils.color_extra import color_to_rgbw, render_color_components
from parrot.utils.colour import Color
from .base import FixtureBase


class Par(FixtureBase):
    pass


class ParRGB(Par):
    def __init__(self, patch):
        super().__init__(patch, "led par", 7)

    def set_dimmer(self, value):
        super().set_dimmer(value)
        self.values[0] = value

    def set_strobe(self, value):
        self.values[4] = value
        super().set_strobe(value)

    def set_color(self, color):
        super().set_color(color)
        self.values[1] = color.red * 255
        self.values[2] = color.green * 255
        self.values[3] = color.blue * 255


class ParRGBAWU(Par):
    "Mountain Lotus Par fixture"

    color_components = [
        Color("red"),
        Color("green"),
        Color("blue"),
        Color("orange"),
        Color("white"),
        Color("violet"),
    ]

    def __init__(self, patch):
        super().__init__(patch, "par rgbawu", 9)

    def set_dimmer(self, value):
        super().set_dimmer(value)
        self.values[0] = value

    def set_strobe(self, value):
        self.values[7] = value
        super().set_strobe(value)

    def set_color(self, color):
        super().set_color(color)
        (r, g, b, w) = color_to_rgbw(color)
        self.values[1] = r
        self.values[2] = g
        self.values[3] = b
        self.values[5] = w
        self.values[6] = b

        # render_color_components(
        #     self.__class__.color_components, color, 255, self.values, 1, 1
        # )
