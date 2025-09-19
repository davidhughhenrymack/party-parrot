#!/usr/bin/env python3

from beartype.claw import beartype_package
import argparse


def parse_arguments():
    parser = argparse.ArgumentParser(description="Parrot DMX Controller")
    parser.add_argument("--profile", action="store_true", help="Enable profiling")
    parser.add_argument(
        "--profile-interval", type=int, default=10, help="Profiling interval in seconds"
    )
    parser.add_argument("--plot", action="store_true", help="Enable plotting")
    parser.add_argument("--web-port", type=int, default=4040, help="Web server port")
    parser.add_argument("--no-web", action="store_true", help="Disable web server")
    parser.add_argument(
        "--vj-fullscreen", action="store_true", help="Run VJ in fullscreen mode"
    )
    return parser.parse_args()


if __name__ == "__main__":
    # Enable beartype runtime type checking for the parrot package
    # beartype_package("parrot")  # Temporarily disabled due to type issues

    from parrot.listeners.mic_to_dmx import MicToDmx

    args = parse_arguments()

    app = MicToDmx(args)
    app.run()
