
usb_path = "/dev/cu.usbserial-EN419206"

import math
from time import sleep
from DMXEnttecPro import Controller

dmx = Controller(usb_path)  # Typical of Linux
par_patch = 19


def clamp(n, min, max):
    if n < min:
        return min
    elif n > max:
        return max
    else:
        return n

def int_clamp_list(items):
    return [int(clamp(item, 0, 255)) for item in items]

def set_par(patch, r, g, b):
    values = int_clamp_list([
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