#!/usr/bin/env python3

from pyftdi.ftdi import Ftdi
import time
import math

def clamp(n, min, max):
    if n < min:
        return min
    elif n > max:
        return max
    else:
        return n

def int_clamp_list(items):
    return [int(clamp(item, 0, 255)) for item in items]

def init_open_dmx(device):
    device.reset()
    device.set_baudrate(3000000/12)
    device.set_line_property(8, 2, "N")
    device.set_flowctrl("")
    device.set_rts(False)
    device.purge_rx_buffer()
    device.purge_tx_buffer()


def set_par(buffer, patch, r, g, b):
    buffer[patch:patch+7] = int_clamp_list([
        255, 
        r, 
        g, 
        b, 
        0, 
        0, 
        0
    ])

def set_mover(buffer, patch, pan, tilt, speed=0, color=0, gobo=0, dimmer=255, shutter=6, function=0, macro=0):
    pan_ts = pan/540*255
    tilt_ts = tilt/270*255
    buffer[patch:patch+11] = int_clamp_list([
        pan_ts,
        (pan_ts - round(pan_ts)) * 255,
        tilt_ts,
        (tilt_ts - round(tilt_ts)) * 255,
        speed,
        color,
        gobo,
        dimmer,
        shutter,
        function,
        macro
    ])


def main():
    device_url = "ftdi://ftdi:232:A10NI4B7/1"
    device = Ftdi.create_from_url(device_url)
    init_open_dmx(device)

    buffer = [int(0)]*512

    frame = 0

    fta = 1/16

    while(True):
        init_open_dmx(device)

        set_par(buffer, 1,  clamp(128*math.sin(frame*fta)+128, 1, 255), clamp(128*math.cos(frame*fta)+128, 1, 255), 0)
        set_par(buffer, 8,  0, clamp(128*math.sin(frame*fta)+128, 1, 255), clamp(128*math.cos(frame*fta)+128, 1, 255))
        set_par(buffer, 14, clamp(128*math.sin(frame*fta)+128, 1, 255), 0, clamp(128*math.cos(frame*fta)+128, 1, 255))

        set_mover(buffer, 29, 360+40*(math.sin(frame*fta)), 30+20*(math.cos(frame*fta)+1), color=46, gobo=10)

        device.set_break(True)
        device.set_break(False)

        device.write_data(bytearray(buffer))
        print("F: " + ', '.join(
            (f"{s:>3}" for s in buffer[0:40])
        ))

        time.sleep(0.020)
        frame += 1
  




if __name__ == "__main__":
    main()