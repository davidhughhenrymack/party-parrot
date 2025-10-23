from DMXEnttecPro import Controller
import math
import os

from beartype import beartype
from parrot.utils.mock_controller import MockDmxController
from .math import clamp
from stupidArtnet import StupidArtnet


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

    def set_channel(self, channel, value):
        # Channels are 1-indexed for DMX, 0-indexed for Art-Net
        if 1 <= channel <= 512:
            self.dmx_data[channel - 1] = int(value)

    def submit(self):
        self.artnet.set(self.dmx_data)
        self.artnet.show()


class MirrorController:
    """Broadcasts DMX commands to multiple controllers"""

    def __init__(self, controllers):
        self.controllers = controllers

    def set_channel(self, channel, value):
        for controller in self.controllers:
            controller.set_channel(channel, value)

    def submit(self):
        for controller in self.controllers:
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
    """Get DMX controller with optional Art-Net mirror based on venue"""
    controllers = []

    # Always add primary DMX controller (Entec or mock)
    entec = get_entec_controller()
    controllers.append(entec)

    # Add Art-Net if configured for this venue
    if venue is not None:
        venue_name = venue.name if hasattr(venue, "name") else str(venue)
        config = artnet_config.get(venue_name)

        if config:
            print(
                f"Art-Net enabled for {venue_name}: {config['ip']} Universe {config['universe']}"
            )
            artnet = ArtNetController(config["ip"], config["universe"])
            controllers.append(artnet)

    # Return single controller or mirror wrapper
    if len(controllers) == 1:
        return controllers[0]
    else:
        return MirrorController(controllers)
