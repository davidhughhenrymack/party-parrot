from parrot.fixtures.base import FixtureBase
from parrot.utils.color_extra import color_to_rgbw
from parrot.utils.math import clamp


class ChauvetDerby(FixtureBase):
    def __init__(self, address):
        super().__init__(address, "chauvet derby", 6)

    def set_color(self, color):
        super().set_color(color)
        c = color_to_rgbw(color)
        for i in range(4):
            self.values[i] = c[i]

    def set_strobe(self, value):
        super().set_strobe(value)
        # Use accumulated strobe_value for DMX output
        self.values[4] = clamp(self.strobe_value, 0, 250)

    def set_speed(self, value):
        self.values[5] = value
        super().set_speed(value)
