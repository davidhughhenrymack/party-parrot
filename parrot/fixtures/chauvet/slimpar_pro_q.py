from parrot.fixtures.base import FixtureBase
from parrot.utils.math import clamp
from parrot.utils.color_extra import dim_color
from parrot.fixtures.led_par import Par


class ChauvetSlimParProQ_5Ch(Par):
    """
    Chauvet DJ SlimPAR Pro Q USB 5 channel mode

    Channel 1: Red intensity (0–100%)
    Channel 2: Green intensity (0–100%)
    Channel 3: Blue intensity (0–100%)
    Channel 4: Amber intensity (0–100%)
    Channel 5: Master dimmer (0–100%)
    """

    def __init__(self, address):
        super().__init__(address, "chauvet slimpar pro q", 5)

    def set_color(self, color):
        super().set_color(color)
        # Set RGB values directly from the color
        self.values[0] = int(color.red * 255)
        self.values[1] = int(color.green * 255)
        self.values[2] = int(color.blue * 255)
        # Amber is approximated based on the warmth of the color
        # This is a simple approximation - amber is often derived from red and green
        self.values[3] = int(min(color.red, color.green) * 255)

    def set_dimmer(self, value):
        super().set_dimmer(value)
        self.values[4] = clamp(int(value * 255), 0, 255)
