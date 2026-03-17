#!/usr/bin/env python3

"""
Constants for the VJ system.
"""

import os

# Standard canvas dimensions for VJ content (overridable via env vars)
DEFAULT_WIDTH = int(os.environ.get("PARROT_CONTENT_WIDTH", "1280"))
DEFAULT_HEIGHT = int(os.environ.get("PARROT_CONTENT_HEIGHT", "720"))

# Common aspect ratios
ASPECT_16_9 = (1920, 1080)
ASPECT_4_3 = (1024, 768)
ASPECT_1_1 = (720, 720)

# Frame rates
DEFAULT_FPS = 30
HIGH_FPS = 60
