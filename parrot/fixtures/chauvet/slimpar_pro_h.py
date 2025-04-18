from parrot.fixtures.base import FixtureBase
from parrot.utils.color_extra import dim_color
from parrot.utils.math import clamp
from parrot.fixtures.led_par import Par


class ChauvetSlimParProH_7Ch(Par):
    """
    Chauvet DJ SlimPAR Pro H USB 7 channel mode

    Channel 1: Master dimmer (0–100%)
    Channel 2: Red intensity (0–100%)
    Channel 3: Green intensity (0–100%)
    Channel 4: Blue intensity (0–100%)
    Channel 5: Amber intensity (0–100%)
    Channel 6: White intensity (0–100%)
    Channel 7: UV (Ultraviolet) intensity (0–100%)
    """

    def __init__(self, address):
        super().__init__(address, "chauvet slimpar pro h", 7)

    def set_dimmer(self, value):
        super().set_dimmer(value)
        self.values[0] = int(((value / 255) ** 2) * 255)

    def set_color(self, color):
        super().set_color(color)
        # Set RGB values directly from the color
        self.values[1] = int(color.red * 255)
        self.values[2] = int(color.green * 255)
        self.values[3] = int(color.blue * 255)

        # Amber is approximated based on the warmth of the color
        # This is a simple approximation - amber is often derived from red and green
        self.values[4] = int(min(color.red, color.green) * 255)

        # White is approximated based on the minimum of RGB values
        self.values[5] = int(min(color.red, color.green, color.blue) * 255)

        # UV is approximated based on the blue and violet components
        # This is a simple approximation
        self.values[6] = int(color.blue * 0.7 * 255)
