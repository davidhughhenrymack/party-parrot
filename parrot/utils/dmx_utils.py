from DMXEnttecPro import Controller
import math
import os

from parrot.utils.mock_controller import MockDmxController
from .math import clamp


def dmx_clamp(n):
    if math.isnan(n):
        return 0
    return int(clamp(n, 0, 255))


def dmx_clamp_list(items):
    return [int(clamp(item, 0, 255)) for item in items]


usb_path = "/dev/cu.usbserial-EN419206"


def get_controller():
    if os.environ.get("MOCK_DMX", False) != False:
        return MockDmxController()

    try:
        return Controller(usb_path)
    except:
        print("Could not connect to DMX controller. Using mock controller instead.")
        return MockDmxController()
