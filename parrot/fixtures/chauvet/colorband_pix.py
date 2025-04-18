from parrot.fixtures.base import FixtureBase, FixtureWithBulbs
from parrot.utils.color_extra import color_to_rgbw, dim_color
from parrot.utils.math import clamp


class ColorBandPixZone(FixtureBase):
    """
    Represents a single zone (3 channels - RGB) in the COLORband PiX fixture
    """

    def __init__(self, address, parent):
        super().__init__(address, "colorband pix zone", 3)
        self.parent = parent

    def render_values(self, values):
        # Apply color with dimming
        parent_dimmer = self.parent.get_dimmer()
        c = dim_color(self.get_color(), self.get_dimmer() / 255 * parent_dimmer / 255)

        values[self.address + 0] = int(c.red * 255)  # Red
        values[self.address + 1] = int(c.green * 255)  # Green
        values[self.address + 2] = int(c.blue * 255)  # Blue


class ChauvetColorBandPiX_36Ch(FixtureWithBulbs):
    """
    Chauvet DJ COLORband PiX IP 36 channel mode

    In the 36-channel mode, each set of three channels controls the Red, Green, and Blue
    intensity for one of the 12 LED zones:

    Channels 1–3: Zone 1 – Red, Green, Blue
    Channels 4–6: Zone 2 – Red, Green, Blue
    ...
    Channels 34–36: Zone 12 – Red, Green, Blue
    """

    def __init__(self, address):
        # Create 12 zone objects, each controlling 3 channels (RGB)
        zones = []
        for i in range(12):
            # The zone's address is relative to the fixture's address
            zone_address = i * 3
            zone = ColorBandPixZone(zone_address, self)
            zones.append(zone)

        super().__init__(address, "chauvet colorband pix", 36, zones)
