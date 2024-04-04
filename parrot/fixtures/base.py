from parrot.utils.colour import Color
from parrot.utils.dmx_utils import dmx_clamp
from parrot.utils.string import kebab_case


class FixtureBase:
    def __init__(self, address, name, width):
        self.address = address
        self.name = name
        self.width = width
        self.values = [0 for i in range(width)]
        self.color_value = Color("black")
        self.dimmer_value = 0

    def set_color(self, color: Color):
        self.color_value = color

    def get_color(self):
        return self.color_value

    def set_dimmer(self, value):
        self.dimmer_value = value

    def get_dimmer(self):
        return self.dimmer_value

    def set_strobe(self, value):
        pass

    def set_pan(self, value):
        pass

    def set_tilt(self, value):
        pass

    def render(self, dmx):
        for i in range(len(self.values)):
            dmx.set_channel(self.address + i, dmx_clamp(self.values[i]))

    def __str__(self) -> str:
        return f"{self.name} @ {self.address}"

    @property
    def id(self):
        return f"{kebab_case(self.name)}@{self.address}"


class ColorWheelEntry:
    def __init__(self, color: Color, dmx_value: int):
        self.color = color
        self.dmx_value = dmx_value


class GoboWheelEntry:
    def __init__(self, gobo: str, dmx_value: int):
        self.gobo = gobo
        self.dmx_value = dmx_value
