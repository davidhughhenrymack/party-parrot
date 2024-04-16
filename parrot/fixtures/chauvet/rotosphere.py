from parrot.fixtures.base import FixtureBase, FixtureWithBulbs
from parrot.utils.color_extra import dim_color, lerp_color, color_distance
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

        distances = [
            (idx, color, color_distance(self.get_color(), color))
            for idx, color in enumerate(color_components)
        ]
        distances = sorted(
            [i for i in distances if i[2] < 0.3], key=lambda i: i[2], reverse=True
        )

        distances = distances[-2:]

        for i in range(len(color_components)):
            values[self.address + i] = 0

        for idx, color, dist in distances:
            dn = (3 - dist) / 3
            dim = self.get_dimmer() / 255
            values[self.address + idx] = int(dn * dim * 255)


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
