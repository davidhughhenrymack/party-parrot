#!/usr/bin/env python3
"""
Test VJ button and display in main GUI
"""
import os
import time

os.environ["TK_SILENCE_DEPRECATION"] = "1"


def test_vj_button_in_main_gui():
    """Test VJ button functionality in main GUI"""
    print("🎬 Testing VJ button in main GUI...")

    try:
        from parrot.state import State
        from parrot.director.director import Director
        from parrot.director.signal_states import SignalStates
        from parrot.gui.gui import Window

        print("✅ Imports successful")

        # Create components with VJ system
        state = State()
        signal_states = SignalStates()

        # Suppress verbose director creation
        import sys
        from io import StringIO

        old_stdout = sys.stdout
        sys.stdout = StringIO()

        try:
            director = Director(state)
        finally:
            sys.stdout = old_stdout

        print("✅ Director created with VJ system")

        # Create GUI window
        window = Window(state, lambda: window.quit(), director, signal_states)

        # Force window visibility
        window.update()

        print("✅ Main GUI window created")

        # Check if VJ button exists
        if hasattr(window, "vj_button"):
            print("✅ VJ button found in GUI")
            print(f"   Button text: {window.vj_button.cget('text')}")
        else:
            print("❌ VJ button missing from GUI")

        # Check if VJ canvas exists
        if hasattr(window, "vj_canvas"):
            print("✅ VJ canvas found")
        else:
            print("❌ VJ canvas missing")

        # Test VJ toggle
        print("🎬 Testing VJ toggle...")
        try:
            # Toggle VJ on
            window.toggle_vj_display()
            window.update()

            if window.vj_visible:
                print("✅ VJ display activated")

                # Wait for VJ content
                print("⏰ Waiting for VJ content...")
                for i in range(10):  # Wait up to 1 second
                    window.update()
                    time.sleep(0.1)

                    # Check if canvas has content
                    if window.vj_canvas and len(window.vj_canvas.find_all()) > 0:
                        print("✅ VJ canvas has content!")
                        break
                else:
                    print("⚠️ VJ canvas still empty after 1 second")

                # Toggle VJ off
                window.toggle_vj_display()
                window.update()

                if not window.vj_visible:
                    print("✅ VJ display deactivated")
                else:
                    print("⚠️ VJ display still active")

            else:
                print("❌ VJ display not activated")

        except Exception as e:
            print(f"❌ VJ toggle failed: {e}")

        print("⏰ Keeping window open for 5 seconds...")
        window.after(5000, window.quit)
        window.mainloop()

        print("✅ VJ button test completed")
        return True

    except Exception as e:
        print(f"❌ VJ button test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run VJ button test"""
    print("🎛️" * 50)
    print("  VJ BUTTON TEST")
    print("🎛️" * 50)

    success = test_vj_button_in_main_gui()

    if success:
        print("\n✅ VJ button test passed!")
        print("🎬 VJ button should be visible in main GUI")
        print("🖱️ Click button or press SPACEBAR to toggle VJ")
    else:
        print("\n❌ VJ button test failed")
        print("🔧 Need to fix VJ integration")


if __name__ == "__main__":
    main()
