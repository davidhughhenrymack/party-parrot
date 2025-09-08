#!/usr/bin/env python3
"""
Verify GUI is working with visual confirmation
"""
import os
import time

os.environ["TK_SILENCE_DEPRECATION"] = "1"


def test_gui_with_confirmation():
    """Test GUI with clear visual confirmation"""
    print("🖥️ Testing GUI with visual confirmation...")

    try:
        import tkinter as tk
        from tkinter import messagebox

        print("✅ Creating test window...")

        # Create a very obvious test window
        root = tk.Tk()
        root.title("🎆 PARTY PARROT GUI TEST 🎆")
        root.configure(bg="red")  # Bright red background
        root.geometry("600x400+200+200")

        # Make it very obvious
        root.lift()
        root.attributes("-topmost", True)
        root.focus_force()

        # Add obvious content
        title_label = tk.Label(
            root,
            text="🎆 PARTY PARROT GUI WORKING! 🎆",
            font=("Arial", 24, "bold"),
            bg="red",
            fg="white",
        )
        title_label.pack(pady=50)

        status_label = tk.Label(
            root,
            text="✅ If you can see this, the GUI is working!\n🎵 VJ system ready for your rave!",
            font=("Arial", 16),
            bg="red",
            fg="yellow",
        )
        status_label.pack(pady=20)

        # Countdown timer
        countdown_var = tk.StringVar()
        countdown_label = tk.Label(
            root, textvariable=countdown_var, font=("Arial", 14), bg="red", fg="white"
        )
        countdown_label.pack(pady=20)

        # Countdown function
        def countdown(seconds):
            if seconds > 0:
                countdown_var.set(f"Window will close in {seconds} seconds...")
                root.after(1000, lambda: countdown(seconds - 1))
            else:
                countdown_var.set("Closing...")
                root.quit()

        # Start countdown
        countdown(10)

        # Update and show
        root.update()
        root.mainloop()

        print("✅ GUI test window completed!")
        return True

    except Exception as e:
        print(f"❌ GUI test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run GUI confirmation test"""
    print("🔍" * 50)
    print("  GUI WORKING CONFIRMATION TEST")
    print("🔍" * 50)

    print("\n🖥️ This test will show a BRIGHT RED window")
    print("👁️ Look for a red window with 'PARTY PARROT GUI WORKING!'")
    print("⏰ Window will stay open for 10 seconds")
    print("")

    success = test_gui_with_confirmation()

    if success:
        print("\n🏆 GUI TEST RESULTS:")
        print("   ✅ GUI window created successfully")
        print("   ✅ Window should have been visible for 10 seconds")
        print("   ✅ If you saw the red window, GUI is working!")
        print("   🚀 Ready to test full Party Parrot application")
    else:
        print("\n❌ GUI test failed - window creation issues")

    return success


if __name__ == "__main__":
    main()
