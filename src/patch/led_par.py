
from .base import BaseFixture

class LedPar(BaseFixture):
    def __init__(self, patch):
        super().__init__(patch, "led par", 7)

    def set_dimmer(self, value):
        self.values[0] = value

    def set_strobe(self, value):
        self.values[4] = value

    def set_color(self, color):
        self.values[1] = color.red * 255
        self.values[2] = color.green * 255
        self.values[3] = color.blue * 255

