#!/usr/bin/env python3

import os
import traceback
from parrot.listeners.mic_to_dmx import MicToDmx

if __name__ == "__main__":
    app = MicToDmx()
    app.run()

    # except Exception as e:
    #     print(traceback.format_exc())
    #     False
