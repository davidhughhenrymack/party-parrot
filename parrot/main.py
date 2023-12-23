#!/usr/bin/env python3

from parrot.listeners.mic_to_dmx_basic import MicToDmxBasic

if __name__ == "__main__":
    audio = MicToDmxBasic()
    while True:
        audio.listen()
