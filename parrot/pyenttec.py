
import math
from time import sleep
from parrot.utils.dmx_utils import dmx_clamp_list
import pyenttec as dmx
port = dmx.select_port()

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
        port.dmx_frame[patch + i] = values[i]
        # dmx.set_channel(patch + i, values[i])

    port.render()

frame = 0
while(True):
    set_par(par_patch, math.sin(frame) * 128 + 128, 0, math.cos(frame) * 128 + 128)
    sleep(0.1)
    frame += 0.1