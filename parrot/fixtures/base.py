from parrot.utils.colour import Color
from parrot.utils.dmx_utils import dmx_clamp


class FixtureBase:
    def __init__(self, address, name, width):
        self.address = address
        self.name = name
        self.width = width
        self.values = [0 for i in range(width)]
        self.color = Color("black")

    def set_color(self, color: Color):
        self.color = color

    def set_dimmer(self, value):
        raise NotImplementedError()

    def set_strobe(self, value):
        raise NotImplementedError()

    def set_pan(self, value):
        raise NotImplementedError()

    def set_tilt(self, value):
        raise NotImplementedError()

    def render(self, dmx):
        for i in range(len(self.values)):
            dmx.set_channel(self.address + i, dmx_clamp(self.values[i]))


class ColorWheelEntry:
    def __init__(self, color: Color, dmx_value: int):
        self.color = color
        self.dmx_value = dmx_value


class GoboWheelEntry:
    def __init__(self, gobo: str, dmx_value: int):
        self.gobo = gobo
        self.dmx_value = dmx_value
