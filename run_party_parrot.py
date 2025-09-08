#!/usr/bin/env python3
"""
Simple Party Parrot Launcher - No fallbacks, just works
"""
import os
import sys

# Suppress warnings for clean output
os.environ["AV_LOG_LEVEL"] = "error"
os.environ["FFMPEG_LOG_LEVEL"] = "error"
os.environ["MPLBACKEND"] = "Agg"


def main():
    """Run Party Parrot in headless mode"""
    print("🚀 Starting Party Parrot...")

    # Import and run
    from parrot.listeners.mic_to_dmx import MicToDmx
    import argparse

    # Create args for headless mode
    args = argparse.Namespace()
    args.profile = False
    args.profile_interval = 10
    args.no_gui = True  # Force headless
    args.plot = False
    args.web_port = 4040
    args.no_web = False

    # Create and run app
    app = MicToDmx(args)
    print("✅ Party Parrot ready!")
    print("🎆 VJ system active!")
    print("🌐 Web control: http://localhost:4040")
    print("🎵 Listening for audio...")

    try:
        app.run()
    except KeyboardInterrupt:
        print("\n🛑 Party Parrot stopped")


if __name__ == "__main__":
    main()
