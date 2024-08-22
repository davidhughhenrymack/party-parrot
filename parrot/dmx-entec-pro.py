
usb_path = "/dev/cu.usbserial-EN419206"

import math
from time import sleep
from DMXEnttecPro import Controller
from parrot.utils.dmx_utils import dmx_clamp_list
from parrot.utils.math import clamp

dmx = Controller(usb_path)  # Typical of Linux
par_patch = 19


def set_par(patch, r, g, b):
    values = dmx_clamp_list([
        255, 
        r, 
        g, 
        b, 
        0, 
        0, 
        0
    ])
    for i in range(len(values)):
        dmx.set_channel(patch + i, values[i])

    dmx.submit()

frame = 0
while(True):
    set_par(par_patch, math.sin(frame) * 128 + 128, 0, math.cos(frame) * 128 + 128)
    sleep(0.1)
    frame += 0.1