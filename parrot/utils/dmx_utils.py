from DMXEnttecPro import Controller
import math
import os
import enum
import serial.tools.list_ports
from serial.serialutil import SerialException

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


@beartype
def find_entec_port():
    import os
    import glob
    import serial.tools.list_ports
    import sys

    # First, try the hardcoded path
    if os.path.exists(usb_path):
        return usb_path

    # macOS-specific tty fallback
    if sys.platform == "darwin":
        tty_path = usb_path.replace("/dev/cu.", "/dev/tty.")
        if os.path.exists(tty_path):
            return tty_path

    ports = serial.tools.list_ports.comports()

    for port in ports:
        desc = str(port.description).lower()
        hwid = str(port.hwid).lower()
        manufacturer = str(getattr(port, "manufacturer", "")).lower()
        product = str(getattr(port, "product", "")).lower()

        if "0403" in hwid and "6001" in hwid:
            return port.device

        if any(
            keyword in desc
            or keyword in hwid
            or keyword in manufacturer
            or keyword in product
            for keyword in ["enttec", "entec", "dmx", "ftdi"]
        ):
            return port.device

    # OS-specific /dev scanning
    if sys.platform == "darwin":
        scan_patterns = [
            "/dev/cu.usbserial*",
            "/dev/cu.usbmodem*",
            "/dev/tty.usbserial*",
            "/dev/tty.usbmodem*",
        ]
    else:  # Linux + others
        scan_patterns = [
            "/dev/ttyUSB*",
            "/dev/ttyACM*",
        ]

    for pattern in scan_patterns:
        for path in glob.glob(pattern):
            if os.path.exists(path):
                return path

    return None


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
        self._shadow: dict[Universe, list[int]] = {
            u: [0] * 512 for u in controller_map
        }
        # Track which universes use Entec controllers for reconnection
        self._entec_universes = set()

    def _mark_entec_universe(self, universe):
        """Mark a universe as using an Entec controller"""
        self._entec_universes.add(universe)

    def set_channel(self, channel, value, universe=Universe.default):
        """Set a channel value on the specified universe"""
        if universe not in self._shadow:
            self._shadow[universe] = [0] * 512
        if 1 <= channel <= 512:
            self._shadow[universe][channel - 1] = dmx_clamp(value)
        controller = self.controller_map.get(universe)
        if controller:
            controller.set_channel(channel, value)

    def snapshot_universe(self, universe: Universe = Universe.default) -> list[int]:
        """Last values routed through this controller (for DMX heatmap UI)."""
        return list(self._shadow.get(universe, [0] * 512))

    def _reconnect_entec(self, universe):
        """Attempt to reconnect the Entec controller for a universe"""
        if universe not in self._entec_universes:
            return False

        try:
            new_controller = get_entec_controller()
            if isinstance(new_controller, Controller):
                self.controller_map[universe] = new_controller
                return True
            else:
                self.controller_map[universe] = new_controller
                # Remove from Entec universes since we're using mock now
                self._entec_universes.discard(universe)
                return False
        except Exception as e:
            print(f"⚠️  Enttec reconnect failed ({universe.value}): {e}")
            self.controller_map[universe] = MockDmxController()
            # Remove from Entec universes since we're using mock now
            self._entec_universes.discard(universe)
            return False

    def submit(self):
        """Submit all controllers"""
        for universe, controller in self.controller_map.items():
            try:
                controller.submit()
            except (SerialException, OSError) as e:
                print(f"⚠️  DMX submit failed ({universe.value}): {e}")
                if universe in self._entec_universes:
                    self._reconnect_entec(universe)


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

    # Try to find the Entec port
    port_path = find_entec_port()
    if port_path is None:
        print("⚠️  Enttec USB DMX Pro not found — using mock DMX output.")
        return MockDmxController()

    # Try to connect with the found port
    try:
        return Controller(port_path)
    except Exception as e:
        if port_path.startswith("/dev/cu."):
            tty_path = port_path.replace("/dev/cu.", "/dev/tty.")
            if os.path.exists(tty_path):
                try:
                    return Controller(tty_path)
                except Exception as e2:
                    print(
                        f"⚠️  Enttec DMX open failed ({port_path}, {tty_path}): {e}; {e2}"
                    )
                    print("⚠️  Using mock DMX output.")
                    return MockDmxController()
        print(f"⚠️  Enttec DMX open failed ({port_path}): {e}")
        print("⚠️  Using mock DMX output.")
        return MockDmxController()


@beartype
def get_controller(venue=None):
    """Get DMX controller with universe routing based on venue"""
    controller_map = {}
    switch_controller = SwitchController(controller_map)

    # Always add primary DMX controller (Entec or mock) as default universe
    entec = get_entec_controller()
    controller_map[Universe.default] = entec

    # Mark as Entec universe if it's a real Controller (not MockDmxController)
    if isinstance(entec, Controller):
        switch_controller._mark_entec_universe(Universe.default)

    # Add Art-Net if configured for this venue
    if venue is not None:
        if hasattr(venue, "slug"):
            venue_name = venue.slug
        elif hasattr(venue, "name"):
            venue_name = venue.name
        else:
            venue_name = str(venue)
        config = artnet_config.get(venue_name)

        if config:
            print(
                f"Art-Net: {venue_name} → {config['ip']} u{config['universe']}"
            )
            artnet = ArtNetController(config["ip"], config["universe"])
            controller_map[Universe.art1] = artnet

    # Always return SwitchController
    return switch_controller
