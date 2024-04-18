from parrot.fixtures.base import FixtureBase, FixtureWithBulbs
from parrot.utils.color_extra import (
    color_distance,
    dim_color,
    lerp_color,
    render_color_components,
)
from parrot.utils.colour import Color
from parrot.utils.math import clamp
from parrot.utils.dmx_utils import dmx_clamp

color_components = [
    Color("red"),
    Color("green"),
    Color("blue"),
    Color("white"),
    Color("cyan"),
    Color("magenta"),
    Color("yellow"),
    Color("orange"),
]


class RotosphereBulb(FixtureBase):
    def __init__(self, address):
        super().__init__(address, "chauvet rotosphere bulb", 8)

    def render_values(self, values):
        render_color_components(
            color_components, self.get_color(), self.get_dimmer(), values, self.address
        )


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
        if value == 0:
            self.values[27] = 0

        else:
            speed_low = 194
            speed_fast = 255
            value = speed_low + (dmx_clamp(value) / 255 * (speed_fast - speed_low))
            self.values[27] = int(value)

    def get_speed(self):
        return self.values[27]
