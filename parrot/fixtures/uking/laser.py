from parrot.fixtures.base import FixtureBase
from parrot.fixtures.chauvet import dmx_layout

dmx_layout = [
    "mode",
    "dimmer1_green",
    "dimmer2_yellow",
    "dimmer3_blue",
    "dimmer4_green",
    "dimmer5_red",
    "pattern",
    "pan",
    "tilt",
    "set postion rotation",
    "rotation",
    "reversing",
    "zoom",
]


class FiveBeamLaser(FixtureBase):
    def __init__(self, address):
        super().__init__(address, "uking 5 beam laser", 13)

        self.set_mode(0)
        self.set_pan(210)
        self.set_tilt(210)
        self.set_pattern(50)

    def set_mode(self, value):
        # 0 - Manual
        self.values[0] = value

    def set_pattern(self, value):
        # 005 - 229: 45 different patterns
        # 230 - 255: dots
        self.values[6] = value

    def set_dimmer(self, value):
        self.values[1] = value
        self.values[2] = value
        self.values[3] = value
        self.values[4] = value
        self.values[5] = value

    def set_pan(self, value):
        # 0 - 199 position
        # 200 - 255 auto move
        self.values[7] = value

    def set_tilt(self, value):
        # 0 - 199 position
        # 200 - 255 auto move
        self.values[8] = value
