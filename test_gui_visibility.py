#!/usr/bin/env python3
"""
Test GUI visibility and positioning on macOS
"""
import os
import sys

# Set environment for macOS
os.environ["TK_SILENCE_DEPRECATION"] = "1"


def test_gui_visibility():
    """Test if GUI window is visible and positioned correctly"""
    print("🔍 Testing GUI visibility...")

    try:
        from parrot.state import State
        from parrot.director.signal_states import SignalStates
        from parrot.gui.gui import Window

        # Disable VJ system temporarily by not creating Director with VJ
        from parrot.director.director import Director

        state = State()
        signal_states = SignalStates()

        print("✅ Creating Director...")
        director = Director(state)
        print("✅ Director created")

        print("✅ Creating Window...")
        window = Window(state, lambda: window.quit(), director, signal_states)
        print("✅ Window object created")

        # Force window to be visible and on top
        window.geometry("800x600+100+100")  # Size and position
        window.lift()  # Bring to front
        window.attributes("-topmost", True)  # Stay on top
        window.focus_force()  # Force focus

        print("✅ Window configured for visibility")

        # Update and display
        window.update_idletasks()
        window.update()

        print("✅ Window updated - should be visible now")
        print("🔍 Checking window state...")

        # Check window state
        try:
            width = window.winfo_width()
            height = window.winfo_height()
            x = window.winfo_x()
            y = window.winfo_y()

            print(f"   Window size: {width}x{height}")
            print(f"   Window position: ({x}, {y})")
            print(f"   Window visible: {window.winfo_viewable()}")
            print(f"   Window mapped: {window.winfo_ismapped()}")

        except Exception as e:
            print(f"   ⚠️ Could not get window info: {e}")

        # Keep window open for 5 seconds
        print("✅ Keeping window open for 5 seconds...")
        window.after(5000, window.quit)
        window.mainloop()

        print("✅ GUI visibility test completed!")
        return True

    except Exception as e:
        print(f"❌ GUI visibility test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run GUI visibility test"""
    print("👁️" * 40)
    print("  GUI VISIBILITY TEST")
    print("👁️" * 40)

    success = test_gui_visibility()

    if success:
        print("\n✅ GUI visibility test passed!")
        print("🖥️ Window should have been visible")
    else:
        print("\n❌ GUI visibility test failed")
        print("🔧 Need to investigate further")

    return success


if __name__ == "__main__":
    main()
