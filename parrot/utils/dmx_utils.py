from DMXEnttecPro import Controller
import math
import os
import enum

from beartype import beartype
from parrot.utils.mock_controller import MockDmxController
from .math import clamp
from stupidArtnet import StupidArtnet


class Universe(enum.Enum):
    """DMX Universe enumeration"""

    default = "default"  # Maps to Entec controller
    art1 = "art1"  # Maps to Art-Net controller


@beartype
def dmx_clamp(n):
    if math.isnan(n):
        return 0
    return int(clamp(n, 0, 255))


@beartype
def dmx_clamp_list(items):
    return [int(clamp(item, 0, 255)) for item in items]


usb_path = "/dev/cu.usbserial-EN419206"


class ArtNetController:
    """Standalone Art-Net controller with DMX controller interface"""

    def __init__(self, artnet_ip="127.0.0.1", artnet_universe=0):
        self.artnet = StupidArtnet(artnet_ip, artnet_universe, 512, 30, True, True)
        self.dmx_data = [0] * 512

    def set_channel(self, channel, value, universe=None):
        # Channels are 1-indexed for DMX, 0-indexed for Art-Net
        # universe parameter is accepted for compatibility but not used (single universe controller)
        if 1 <= channel <= 512:
            self.dmx_data[channel - 1] = int(value)

    def submit(self):
        self.artnet.set(self.dmx_data)
        self.artnet.show()


class SwitchController:
    """Routes DMX commands to the appropriate controller based on universe"""

    def __init__(self, controller_map):
        """
        Initialize with a mapping of Universe -> controller

        Args:
            controller_map: Dict mapping Universe enum values to controller instances
        """
        self.controller_map = controller_map

    def set_channel(self, channel, value, universe=Universe.default):
        """Set a channel value on the specified universe"""
        controller = self.controller_map.get(universe)
        if controller:
            controller.set_channel(channel, value)

    def submit(self):
        """Submit all controllers"""
        for controller in self.controller_map.values():
            controller.submit()


# Per-venue Art-Net configuration
# Format: {venue: {"ip": "x.x.x.x", "universe": 0}}
artnet_config = {
    "mtn_lotus": {"ip": "192.168.100.113", "universe": 0},
}


@beartype
def get_entec_controller():
    """Get Entec controller or mock if not available"""
    if os.environ.get("MOCK_DMX", False) != False:
        return MockDmxController()

    try:
        return Controller(usb_path)
    except Exception as e:
        print(f"Could not connect to Entec DMX controller: {e}")
        print("Using mock DMX controller")
        return MockDmxController()


@beartype
def get_controller(venue=None):
    """Get DMX controller with universe routing based on venue"""
    controller_map = {}

    # Always add primary DMX controller (Entec or mock) as default universe
    entec = get_entec_controller()
    controller_map[Universe.default] = entec

    # Add Art-Net if configured for this venue
    if venue is not None:
        venue_name = venue.name if hasattr(venue, "name") else str(venue)
        config = artnet_config.get(venue_name)

        if config:
            print(
                f"Art-Net enabled for {venue_name}: {config['ip']} Universe {config['universe']}"
            )
            artnet = ArtNetController(config["ip"], config["universe"])
            controller_map[Universe.art1] = artnet

    # Always return SwitchController
    return SwitchController(controller_map)
