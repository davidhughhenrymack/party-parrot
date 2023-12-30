#!/usr/bin/env python3

import traceback
from parrot.listeners.mic_to_dmx_basic import MicToDmxBasic

if __name__ == "__main__":
    audio = MicToDmxBasic()
    while True:
        try:
            audio.listen()
        except (KeyboardInterrupt, SystemExit) as e:
            break
        except Exception as e:
            print(traceback.format_exc())
            False
