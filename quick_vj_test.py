#!/usr/bin/env python3
"""
Quick test of VJ video orientation and pure display
"""
import os
import time
import tkinter as tk
import numpy as np

os.environ["TK_SILENCE_DEPRECATION"] = "1"


def test_vj_display():
    """Test VJ display with fixed video orientation"""
    try:
        from parrot.state import State
        from parrot.director.vj_director import VJDirector
        from parrot.director.frame import Frame, FrameSignal
        from parrot.director.color_scheme import ColorScheme
        from parrot.director.mode import Mode
        from parrot.utils.colour import Color
        from PIL import Image, ImageTk

        print("🎬 Testing VJ display...")

        # Create VJ system
        state = State()
        state.set_mode(Mode.rave)

        # Suppress verbose output
        import sys
        from io import StringIO

        old_stdout = sys.stdout
        sys.stdout = StringIO()

        try:
            vj_director = VJDirector(state, width=800, height=600)
        finally:
            sys.stdout = old_stdout

        # Create pure VJ window
        root = tk.Tk()
        root.title("Pure VJ Test")
        root.configure(bg="black")
        root.geometry("800x600+100+100")
        root.overrideredirect(True)  # No window decorations

        # Make visible
        root.lift()
        root.attributes("-topmost", True)
        root.focus_force()

        # Pure video canvas - NO UI ELEMENTS
        canvas = tk.Canvas(
            root,
            width=800,
            height=600,
            bg="black",
            borderwidth=0,
            highlightthickness=0,
            cursor="none",
        )
        canvas.pack()

        print("✅ Pure VJ window created (no UI elements)")

        frame_count = 0

        def update_display():
            nonlocal frame_count

            try:
                # Create audio frame
                frame = Frame(
                    {
                        FrameSignal.freq_low: 0.8,
                        FrameSignal.freq_high: 0.7,
                        FrameSignal.freq_all: 0.75,
                        FrameSignal.sustained_low: 0.6,
                    }
                )
                scheme = ColorScheme(Color("red"), Color("gold"), Color("cyan"))

                # Get VJ frame
                vj_frame = vj_director.step(frame, scheme)

                if vj_frame is not None and vj_frame.size > 0:
                    # Convert with fixed orientation
                    rgb_frame = vj_frame[:, :, :3].astype(np.uint8)
                    pil_image = Image.fromarray(rgb_frame)
                    photo = ImageTk.PhotoImage(pil_image)

                    # Display pure video
                    canvas.delete("all")
                    canvas.create_image(0, 0, anchor="nw", image=photo)
                    canvas.image = photo

                    if frame_count % 20 == 0:
                        coverage = (np.count_nonzero(vj_frame) / vj_frame.size) * 100
                        print(f"Frame {frame_count}: {coverage:.1f}% coverage")

                frame_count += 1

            except Exception as e:
                print(f"Error: {e}")
                canvas.delete("all")
                canvas.create_rectangle(0, 0, 800, 600, fill="black")

            root.after(50, update_display)  # 20 FPS

        # Bind ESC to quit
        root.bind("<KeyPress-Escape>", lambda e: root.quit())

        # Start updates
        update_display()

        print("📺 Pure VJ display running (ESC to quit)...")
        print("🎬 Should show video right-side up with no UI!")

        # Run for 8 seconds
        root.after(8000, root.quit)
        root.mainloop()

        vj_director.cleanup()
        print("✅ VJ test completed")

    except Exception as e:
        print(f"❌ VJ test failed: {e}")


if __name__ == "__main__":
    test_vj_display()
