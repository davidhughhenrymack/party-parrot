#!/usr/bin/env python3

from parrot.listeners.mic_to_dmx import MicToDmx

import argparse


def parse_arguments():
    parser = argparse.ArgumentParser(description="Parrot DMX Controller")
    parser.add_argument("--profile", action="store_true", help="Enable profiling")
    parser.add_argument(
        "--profile-interval", type=int, default=10, help="Profiling interval in seconds"
    )
    parser.add_argument("--no-gui", action="store_true", help="Disable GUI")
    parser.add_argument("--plot", action="store_true", help="Enable plotting")
    return parser.parse_args()


if __name__ == "__main__":
    args = parse_arguments()

    app = MicToDmx(args)
    app.run()
