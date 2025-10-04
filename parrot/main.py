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
    parser.add_argument(
        "--legacy-gui", action="store_true", help="Use legacy tkinter GUI (deprecated)"
    )
    parser.add_argument(
        "--debug-frame",
        action="store_true",
        help="Capture frame 20 and exit for debugging",
    )
    parser.add_argument(
        "--screenshot",
        action="store_true",
        help="Capture screenshot after 0.5s and exit",
    )
    parser.add_argument(
        "--start-with-overlay",
        action="store_true",
        help="Start with overlay UI visible",
    )
    parser.add_argument(
        "--rave",
        action="store_true",
        help="Start in rave mode",
    )
    parser.add_argument(
        "--fixture-mode",
        action="store_true",
        help="Start in fixture renderer mode (toggle with backslash)",
    )
    return parser.parse_args()


if __name__ == "__main__":
    # Enable beartype runtime type checking for the parrot package
    # beartype_package("parrot")  # Temporarily disabled due to type issues

    import sys

    args = parse_arguments()

    # Use legacy tkinter GUI if requested, otherwise use modern GL window
    if args.legacy_gui:
        print("⚠️  Using legacy tkinter GUI (deprecated)")
        from parrot.listeners.mic_to_dmx import MicToDmx

        app = MicToDmx(args)
        app.run()
    else:
        from parrot.gl_window_app import run_gl_window_app

        run_gl_window_app(args)
