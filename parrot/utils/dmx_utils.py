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
    """Find the Entec DMX controller port automatically"""
    # First, try the hardcoded path if it exists
    if os.path.exists(usb_path):
        print(f"Found Entec port at hardcoded path: {usb_path}")
        return usb_path

    # Try the tty variant (macOS sometimes needs this)
    tty_path = usb_path.replace("/dev/cu.", "/dev/tty.")
    if os.path.exists(tty_path):
        print(f"Found Entec port at tty variant: {tty_path}")
        return tty_path

    # Scan for Entec devices using pyserial
    ports = serial.tools.list_ports.comports()
    print(f"Scanning {len(ports)} serial ports for Entec DMX controller...")
    for port in ports:
        desc = str(port.description).lower()
        hwid = str(port.hwid).lower()
        manufacturer = str(getattr(port, "manufacturer", "")).lower()
        product = str(getattr(port, "product", "")).lower()

        # Check for FTDI VID:PID (0403:6001 is common FTDI chip)
        # Entec DMX USB PRO uses FTDI chip with VID 0403, PID 6001
        if "0403" in hwid and "6001" in hwid:
            print(
                f"Found FTDI device (likely Entec) at {port.device} (VID:PID=0403:6001)"
            )
            if port.device.startswith("/dev/cu."):
                return port.device
            elif port.device.startswith("/dev/tty."):
                cu_path = port.device.replace("/dev/tty.", "/dev/cu.")
                if os.path.exists(cu_path):
                    return cu_path
                return port.device

        # Look for Entec/FTDI DMX devices - check multiple fields
        if any(
            keyword in desc
            or keyword in hwid
            or keyword in manufacturer
            or keyword in product
            for keyword in ["enttec", "entec", "dmx", "ftdi"]
        ):
            print(
                f"Found potential Entec device at {port.device} (desc={port.description}, hwid={port.hwid})"
            )
            # Prefer cu.* over tty.* on macOS for writing
            if port.device.startswith("/dev/cu."):
                return port.device
            elif port.device.startswith("/dev/tty."):
                # Try the cu.* variant
                cu_path = port.device.replace("/dev/tty.", "/dev/cu.")
                if os.path.exists(cu_path):
                    return cu_path
                return port.device

    # Also check for USB serial devices by scanning /dev directly
    # Look for devices matching common patterns
    import glob

    usb_patterns = [
        "/dev/cu.usbserial*",
        "/dev/cu.usbmodem*",
        "/dev/tty.usbserial*",
        "/dev/tty.usbmodem*",
    ]

    print("Scanning /dev for USB serial devices...")
    for pattern in usb_patterns:
        for path in glob.glob(pattern):
            # Skip known non-DMX devices
            if any(skip in path.lower() for skip in ["bluetooth", "debug"]):
                continue
            # Check if it might be our device by checking if it's accessible
            if os.path.exists(path):
                print(f"Found USB serial device at {path}, attempting to verify...")
                # Try to verify it's an FTDI device by checking VID/PID via system_profiler
                # For now, return the first USB serial device found
                # (The Controller class will handle if it's wrong)
                return path

    print("No Entec DMX controller port found")
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
        # Track which universes use Entec controllers for reconnection
        self._entec_universes = set()

    def _mark_entec_universe(self, universe):
        """Mark a universe as using an Entec controller"""
        self._entec_universes.add(universe)

    def set_channel(self, channel, value, universe=Universe.default):
        """Set a channel value on the specified universe"""
        controller = self.controller_map.get(universe)
        if controller:
            controller.set_channel(channel, value)

    def _reconnect_entec(self, universe):
        """Attempt to reconnect the Entec controller for a universe"""
        if universe not in self._entec_universes:
            return False

        print(
            f"🔄 Attempting to reconnect Entec DMX controller for universe {universe.value}..."
        )
        try:
            new_controller = get_entec_controller()
            if isinstance(new_controller, Controller):
                self.controller_map[universe] = new_controller
                print(
                    f"✅ Successfully reconnected Entec DMX controller for universe {universe.value}"
                )
                return True
            else:
                print(
                    f"⚠️  Entec controller not available, using mock controller for universe {universe.value}"
                )
                self.controller_map[universe] = new_controller
                # Remove from Entec universes since we're using mock now
                self._entec_universes.discard(universe)
                return False
        except Exception as e:
            print(f"❌ Failed to reconnect Entec DMX controller: {e}")
            print(f"   Using mock controller for universe {universe.value}")
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
                # Device may have disconnected - print error and attempt reconnect
                print(f"⚠️  DMX controller crash for universe {universe.value}: {e}")
                # Only attempt reconnection for Entec controllers
                if universe in self._entec_universes:
                    print(f"   Attempting to reconnect...")
                    self._reconnect_entec(universe)
                else:
                    print(f"   Skipping reconnection (not an Entec controller)")


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
        print("⚠️  Could not find Entec DMX controller port")
        print("   Troubleshooting steps:")
        print("   1. Make sure the Entec DMX USB PRO is plugged in")
        print("   2. Check System Information > USB to see if the device appears")
        print("   3. Try unplugging and replugging the device")
        print(
            "   4. Install FTDI drivers if needed: https://ftdichip.com/drivers/vcp-drivers/"
        )
        print("   5. Check if the device appears under a different name")
        print("   Using mock DMX controller")
        return MockDmxController()

    # Try to connect with the found port
    try:
        return Controller(port_path)
    except Exception as e:
        # If cu.* fails, try tty.* variant (macOS specific)
        if port_path.startswith("/dev/cu."):
            tty_path = port_path.replace("/dev/cu.", "/dev/tty.")
            if os.path.exists(tty_path):
                try:
                    return Controller(tty_path)
                except Exception as e2:
                    print(
                        f"Could not connect to Entec DMX controller at {port_path}: {e}"
                    )
                    print(
                        f"Could not connect to Entec DMX controller at {tty_path}: {e2}"
                    )
        else:
            print(f"Could not connect to Entec DMX controller at {port_path}: {e}")
        print("Using mock DMX controller")
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
        venue_name = venue.name if hasattr(venue, "name") else str(venue)
        config = artnet_config.get(venue_name)

        if config:
            print(
                f"Art-Net enabled for {venue_name}: {config['ip']} Universe {config['universe']}"
            )
            artnet = ArtNetController(config["ip"], config["universe"])
            controller_map[Universe.art1] = artnet

    # Always return SwitchController
    return switch_controller
