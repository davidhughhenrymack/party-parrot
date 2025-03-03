from parrot.fixtures.base import FixtureBase, FixtureWithBulbs
from parrot.utils.color_extra import color_to_rgbw, dim_color
from parrot.utils.math import clamp


class ColorBandPixZone(FixtureBase):
    """
    Represents a single zone (3 channels - RGB) in the COLORband PiX fixture
    """

    def __init__(self, address):
        super().__init__(address, "colorband pix zone", 3)

    def render_values(self, values):
        # Apply color with dimming
        c = dim_color(self.get_color(), self.get_dimmer() / 255)

        # Calculate the relative offset within the parent fixture's values array
        # This is important because the address is absolute, but values is relative to the fixture
        offset = self.address - values.address if hasattr(values, "address") else 0

        # Set RGB values
        values[offset + 0] = int(c.red * 255)  # Red
        values[offset + 1] = int(c.green * 255)  # Green
        values[offset + 2] = int(c.blue * 255)  # Blue


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
            zone = ColorBandPixZone(zone_address)
            zones.append(zone)

        super().__init__(address, "chauvet colorband pix", 36, zones)

    def set_zone_color(self, zone_index, color):
        """
        Set the color for a specific zone (0-11)
        """
        if 0 <= zone_index < len(self.bulbs):
            self.bulbs[zone_index].set_color(color)

    def get_zones(self):
        """
        Return all zones (same as get_bulbs but with a more descriptive name)
        """
        return self.get_bulbs()
