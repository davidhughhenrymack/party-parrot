#!/usr/bin/env python3
"""
Test GUI focus and visibility issues on macOS
"""
import os
import time

# macOS environment setup
os.environ["TK_SILENCE_DEPRECATION"] = "1"


def test_gui_with_focus_fixes():
    """Test GUI with macOS focus fixes"""
    print("🔍 Testing GUI with macOS focus fixes...")

    try:
        import tkinter as tk
        from parrot.state import State
        from parrot.director.director import Director
        from parrot.director.signal_states import SignalStates
        from parrot.gui.gui import Window

        print("✅ All imports successful")

        # Create components
        state = State()
        signal_states = SignalStates()
        director = Director(state)

        print("✅ Components created")

        # Create window with macOS fixes
        window = Window(state, lambda: window.quit(), director, signal_states)

        # macOS-specific fixes for window visibility
        window.lift()  # Bring to front
        window.attributes("-topmost", True)  # Stay on top temporarily
        window.focus_force()  # Force focus
        window.update()

        # Set a reasonable size and position
        window.geometry("1000x700+50+50")
        window.update()

        print("✅ Window should now be visible!")
        print("🖥️ Window info:")
        print(f"   Size: {window.winfo_width()}x{window.winfo_height()}")
        print(f"   Position: ({window.winfo_x()}, {window.winfo_y()})")
        print(f"   Visible: {window.winfo_viewable()}")
        print(f"   Mapped: {window.winfo_ismapped()}")

        # Remove topmost after showing
        window.after(1000, lambda: window.attributes("-topmost", False))

        # Keep window open for testing
        print("⏰ Window will stay open for 8 seconds...")
        window.after(8000, window.quit)

        # Start the GUI loop
        window.mainloop()

        print("✅ GUI focus test completed successfully!")
        return True

    except Exception as e:
        print(f"❌ GUI focus test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run GUI focus test"""
    print("👁️" * 50)
    print("  GUI FOCUS AND VISIBILITY TEST")
    print("👁️" * 50)

    success = test_gui_with_focus_fixes()

    if success:
        print("\n🏆 GUI is working and should be visible!")
        print("✅ Ready to test full application")
    else:
        print("\n❌ GUI still has issues")
        print("🔧 Need further investigation")

    return success


if __name__ == "__main__":
    main()
