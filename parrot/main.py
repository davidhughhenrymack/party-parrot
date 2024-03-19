#!/usr/bin/env python3

import os
import traceback
from parrot.listeners.mic_to_dmx_basic import MicToDmxBasic

if __name__ == "__main__":
    app = MicToDmxBasic()
    app.run()

    # except Exception as e:
    #     print(traceback.format_exc())
    #     False
