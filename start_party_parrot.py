#!/usr/bin/env python3
"""
Safe Party Parrot Startup Script
Handles macOS Tkinter issues and provides graceful fallbacks
"""
import os
import sys
import argparse


def setup_macos_environment():
    """Setup environment variables for macOS compatibility"""
    # Suppress video conversion warnings
    os.environ["AV_LOG_LEVEL"] = "error"
    os.environ["FFMPEG_LOG_LEVEL"] = "error"

    # Suppress OpenGL warnings
    os.environ["GL_SILENCE_DEPRECATION"] = "1"

    # Force matplotlib backend for macOS
    os.environ["MPLBACKEND"] = "Agg"  # Use non-interactive backend

    print("🍎 macOS environment configured for Party Parrot")


def parse_arguments():
    parser = argparse.ArgumentParser(
        description="Party Parrot DMX Controller - Safe Startup"
    )
    parser.add_argument("--profile", action="store_true", help="Enable profiling")
    parser.add_argument(
        "--profile-interval", type=int, default=10, help="Profiling interval in seconds"
    )
    parser.add_argument("--no-gui", action="store_true", help="Disable GUI")
    parser.add_argument(
        "--force-headless",
        action="store_true",
        help="Force headless mode (no GUI attempts)",
    )
    parser.add_argument("--plot", action="store_true", help="Enable plotting")
    parser.add_argument("--web-port", type=int, default=4040, help="Web server port")
    parser.add_argument("--no-web", action="store_true", help="Disable web server")
    parser.add_argument(
        "--vj-only", action="store_true", help="Run VJ system only (for testing)"
    )
    return parser.parse_args()


def test_vj_system_only():
    """Test VJ system in isolation"""
    print("🎬" * 50)
    print("  VJ SYSTEM ISOLATED TEST")
    print("🎬" * 50)

    try:
        from parrot.state import State
        from parrot.director.vj_director import VJDirector
        from parrot.director.mode import Mode
        from parrot.director.frame import Frame, FrameSignal
        from parrot.director.color_scheme import ColorScheme
        from parrot.utils.colour import Color

        print("✅ VJ imports successful")

        # Create VJ system
        state = State()
        state.set_mode(Mode.rave)

        vj_director = VJDirector(state, width=1920, height=1080)
        print("✅ VJ Director created successfully")

        # Test rendering
        frame = Frame(
            {
                FrameSignal.freq_low: 0.8,
                FrameSignal.freq_high: 0.7,
                FrameSignal.freq_all: 0.75,
            }
        )
        scheme = ColorScheme(Color("gold"), Color("purple"), Color("cyan"))

        print("🎆 Testing VJ rendering...")
        result = vj_director.step(frame, scheme)

        if result is not None:
            print(f"✅ VJ render successful: {result.shape}")
            print(
                f"🎨 Coverage: {(result.sum() / (result.shape[0] * result.shape[1] * 255 * 4)) * 100:.1f}%"
            )
        else:
            print("⚠️ VJ render returned None")

        # Test scene shift
        print("🔄 Testing scene shift...")
        vj_director.shift_vj_interpreters()
        print("✅ Scene shift successful")

        # Performance test
        import time

        render_times = []
        for i in range(5):
            start = time.time()
            result = vj_director.step(frame, scheme)
            render_time = time.time() - start
            render_times.append(render_time)
            print(f"   Render {i+1}: {render_time*1000:.1f}ms")

        avg_time = sum(render_times) / len(render_times)
        fps = 1.0 / avg_time if avg_time > 0 else 0

        print(f"📊 Performance: {avg_time*1000:.1f}ms avg, {fps:.0f} FPS")

        # Cleanup
        vj_director.cleanup()
        print("✅ VJ system test complete - working perfectly!")

        return True

    except Exception as e:
        print(f"❌ VJ system test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def safe_main():
    """Safely start Party Parrot with proper error handling"""
    args = parse_arguments()

    # Setup macOS environment
    if sys.platform == "darwin":  # macOS
        setup_macos_environment()

    # VJ-only mode for testing
    if args.vj_only:
        success = test_vj_system_only()
        sys.exit(0 if success else 1)

    # Force headless mode if requested
    if args.force_headless:
        args.no_gui = True
        print("🖥️ Running in forced headless mode")

    try:
        print("🚀 Starting Party Parrot...")

        # Import and create the main application
        from parrot.listeners.mic_to_dmx import MicToDmx

        app = MicToDmx(args)

        print("✅ Party Parrot initialized successfully!")
        print("🎆 VJ system ready for your Dead Sexy rave!")

        if args.no_gui:
            print("🖥️ Running in headless mode (no GUI)")
            print("🌐 Web interface available at http://localhost:4040")
        else:
            print("🖥️ GUI interface active")
            print("⌨️  Press SPACEBAR to toggle VJ display")

        print("🎵 Listening for audio...")
        print("🎭 Ready for legendary rave performance!")

        app.run()

    except KeyboardInterrupt:
        print("\n🛑 Party Parrot stopped by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Party Parrot crashed: {e}")
        print("🔧 Trying recovery options...")

        # Try headless mode as fallback
        if not args.no_gui:
            print("🖥️ Attempting headless mode...")
            args.no_gui = True
            try:
                app = MicToDmx(args)
                print("✅ Headless mode successful!")
                app.run()
            except Exception as e2:
                print(f"❌ Headless mode also failed: {e2}")
                print("🔧 Please check system requirements")
                sys.exit(1)
        else:
            print("❌ Already in headless mode, cannot recover")
            import traceback

            traceback.print_exc()
            sys.exit(1)


if __name__ == "__main__":
    safe_main()
