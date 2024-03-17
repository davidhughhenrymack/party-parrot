from parrot.fixtures.base import FixtureBase

dmx_layout = [
    "mode",
    "pattern",
    "angle_control",
    "horizontal_angle",
    "vertical_angle",
    "horizontal_position",
    "vertical_position",
    "size",
    "color",
    "dots",
]


class TwoBeamLaser(FixtureBase):
    def __init__(self, address):
        super().__init__(address, "oultia 2 beam laser", 10)

        self.set_pattern(14)

        self.values[2] = 204
        self.values[3] = 102
        self.values[4] = 170
        self.values[5] = 135

    def set_mode(self, value):
        # 0 - Manual
        self.values[0] = value

    def set_pattern(self, value):
        # 005 - 229: 45 different patterns
        # 230 - 255: dots
        self.values[1] = value

    def set_dimmer(self, value):
        if value == 0:
            self.set_mode(0)
        else:
            self.set_mode(69)
