#!/usr/bin/env python3
"""
Test VJ content display with actual rendering
"""
import os
import time
import tkinter as tk
import numpy as np

os.environ["TK_SILENCE_DEPRECATION"] = "1"


def test_vj_content_display():
    """Test actual VJ content display"""
    print("🎨 Testing VJ content display...")

    try:
        from parrot.state import State
        from parrot.director.vj_director import VJDirector
        from parrot.director.frame import Frame, FrameSignal
        from parrot.director.color_scheme import ColorScheme
        from parrot.director.mode import Mode
        from parrot.utils.colour import Color
        from PIL import Image, ImageTk

        # Create VJ system
        state = State()
        state.set_mode(Mode.rave)

        # Suppress verbose initialization
        import sys
        from io import StringIO

        old_stdout = sys.stdout
        sys.stdout = StringIO()

        try:
            vj_director = VJDirector(state, width=400, height=300)
        finally:
            sys.stdout = old_stdout

        print("✅ VJ system created")

        # Create Tkinter window
        root = tk.Tk()
        root.title("🎨 VJ Content Test")
        root.geometry("500x400+100+100")
        root.configure(bg="black")

        # Make visible
        root.lift()
        root.attributes("-topmost", True)
        root.focus_force()

        # Create canvas
        canvas = tk.Canvas(root, width=400, height=300, bg="black", cursor="none")
        canvas.pack(padx=10, pady=10)

        # Status label
        status = tk.Label(root, text="🎬 Starting VJ...", bg="black", fg="white")
        status.pack()

        print("✅ Display window ready")

        frame_count = 0

        def update_vj():
            nonlocal frame_count

            try:
                # Create high-energy frame for maximum effects
                frame = Frame(
                    {
                        FrameSignal.freq_low: 0.8 + 0.2 * np.sin(frame_count * 0.1),
                        FrameSignal.freq_high: 0.7 + 0.3 * np.cos(frame_count * 0.15),
                        FrameSignal.freq_all: 0.75 + 0.25 * np.sin(frame_count * 0.08),
                        FrameSignal.sustained_low: 0.6,
                        FrameSignal.sustained_high: 0.5,
                    }
                )

                scheme = ColorScheme(Color("red"), Color("gold"), Color("cyan"))

                # Step VJ system
                vj_frame = vj_director.step(frame, scheme)

                if vj_frame is not None and vj_frame.size > 0:
                    # Convert and display
                    rgb_frame = vj_frame[:, :, :3].astype(np.uint8)
                    pil_image = Image.fromarray(rgb_frame)
                    photo = ImageTk.PhotoImage(pil_image)

                    canvas.delete("all")
                    canvas.create_image(0, 0, anchor="nw", image=photo)
                    canvas.image = photo

                    # Update status
                    coverage = (np.count_nonzero(vj_frame) / vj_frame.size) * 100
                    status.config(
                        text=f"🎆 VJ Active - Frame {frame_count} - {coverage:.1f}% coverage"
                    )

                else:
                    # Show "no content" pattern
                    canvas.delete("all")
                    canvas.create_rectangle(0, 0, 400, 300, fill="red", outline="white")
                    canvas.create_text(
                        200,
                        150,
                        text="❌ NO VJ FRAME",
                        fill="white",
                        font=("Arial", 16),
                    )
                    status.config(text=f"❌ No VJ frame - Frame {frame_count}")

                frame_count += 1

                # Trigger scene shift occasionally
                if frame_count % 300 == 0:  # Every 10 seconds
                    vj_director.shift_vj_interpreters()
                    status.config(text=f"🔄 Scene shift - Frame {frame_count}")

            except Exception as e:
                canvas.delete("all")
                canvas.create_rectangle(0, 0, 400, 300, fill="orange", outline="red")
                canvas.create_text(200, 150, text=f"ERROR: {str(e)[:20]}", fill="white")
                status.config(text=f"⚠️ Error: {e}")
                print(f"VJ update error: {e}")

            # Continue updates
            root.after(100, update_vj)  # 10 FPS

        # Start updates
        update_vj()

        print("🎬 VJ content test running for 15 seconds...")
        print("👁️ You should see colorful VJ content!")

        # Run for 15 seconds
        root.after(15000, root.quit)
        root.mainloop()

        vj_director.cleanup()
        print("✅ VJ content test completed")
        return True

    except Exception as e:
        print(f"❌ VJ content test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


if __name__ == "__main__":
    test_vj_content_display()
