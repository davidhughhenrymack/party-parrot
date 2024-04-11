from parrot.fixtures.base import FixtureBase, FixtureWithBulbs
from parrot.utils.color_extra import dim_color, lerp_color
from parrot.utils.colour import Color
from parrot.utils.math import clamp


class RotosphereBulb(FixtureBase):
    def __init__(self, address):
        super().__init__(address, "chauvet rotosphere bulb", 8)

    def render_values(self, values):
        c = dim_color(self.get_color(), self.get_dimmer() / 255)
        rgb = c.get_rgb()
        white = c.get_luminance()

        channels = ["cyan", "magenta", "yellow", "orange"]
        components = {}

        for channel in channels:
            components[channel] = (
                clamp(180 - abs(Color(channel).get_hue() - c.get_hue()) / 180, 0, 1)
                * c.get_saturation()
                * c.get_luminance()
            )

        values[self.address] = rgb[0]
        values[self.address + 1] = rgb[1]
        values[self.address + 2] = rgb[2]
        values[self.address + 3] = white
        values[self.address + 4] = components["cyan"]
        values[self.address + 5] = components["magenta"]
        values[self.address + 6] = components["yellow"]
        values[self.address + 7] = components["orange"]


class ChauvetRotosphere_28Ch(FixtureWithBulbs):

    def __init__(
        self,
        address,
    ):
        super().__init__(
            address, "chauvet rotosphere", 28, [RotosphereBulb(i * 8) for i in range(3)]
        )

    def set_strobe(self, value):
        self.values[24] = value

    def set_speed(self, value):
        self.values[27] = value

    def get_speed(self):
        return self.values[27]
