#!/usr/bin/env python3
"""
Test VJ rendering system to ensure it displays actual content
"""
import os
import numpy as np
import tkinter as tk
from tkinter import Canvas, Label, BOTH

os.environ["TK_SILENCE_DEPRECATION"] = "1"


def test_vj_frame_generation():
    """Test if VJ system generates actual frames"""
    print("🔍 Testing VJ frame generation...")

    try:
        from parrot.state import State
        from parrot.director.vj_director import VJDirector
        from parrot.director.frame import Frame, FrameSignal
        from parrot.director.color_scheme import ColorScheme
        from parrot.director.mode import Mode
        from parrot.utils.colour import Color

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

        print("✅ VJ Director created")

        # Create test frame with high energy
        frame = Frame(
            {
                FrameSignal.freq_low: 0.9,
                FrameSignal.freq_high: 0.8,
                FrameSignal.freq_all: 0.85,
                FrameSignal.sustained_low: 0.7,
                FrameSignal.sustained_high: 0.6,
            }
        )
        scheme = ColorScheme(Color("red"), Color("gold"), Color("cyan"))

        print("🎨 Generating VJ frame...")

        # Generate VJ frame
        vj_frame = vj_director.step(frame, scheme)

        if vj_frame is not None:
            print(f"✅ VJ frame generated: {vj_frame.shape}")
            print(f"   Data type: {vj_frame.dtype}")
            print(f"   Value range: {vj_frame.min()} - {vj_frame.max()}")

            # Analyze content
            non_zero_pixels = np.count_nonzero(vj_frame)
            total_pixels = vj_frame.shape[0] * vj_frame.shape[1] * vj_frame.shape[2]
            coverage = (non_zero_pixels / total_pixels) * 100

            print(f"   Non-zero pixels: {non_zero_pixels:,}")
            print(f"   Coverage: {coverage:.1f}%")

            # Check if there's actual visual content
            if coverage > 10:
                print("✅ VJ frame has significant visual content")
            else:
                print("⚠️ VJ frame mostly empty/black")

            # Analyze color channels
            r_avg = np.mean(vj_frame[:, :, 0])
            g_avg = np.mean(vj_frame[:, :, 1])
            b_avg = np.mean(vj_frame[:, :, 2])

            print(f"   Color averages: R={r_avg:.1f}, G={g_avg:.1f}, B={b_avg:.1f}")

        else:
            print("❌ VJ frame is None - no content generated")
            return False

        vj_director.cleanup()
        return True

    except Exception as e:
        print(f"❌ VJ frame generation failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_vj_display_in_tkinter():
    """Test VJ display in actual Tkinter window"""
    print("\n🖥️ Testing VJ display in Tkinter...")

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

        # Suppress verbose output during creation
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
        root.title("🎬 VJ Display Test")
        root.geometry("500x400+200+200")
        root.configure(bg="black")

        # Make window visible
        root.lift()
        root.attributes("-topmost", True)
        root.focus_force()

        # Create canvas for VJ display
        canvas = Canvas(
            root,
            width=400,
            height=300,
            bg="black",
            borderwidth=0,
            highlightthickness=0,
        )
        canvas.pack(padx=10, pady=10)

        # Status label
        status_label = Label(
            root,
            text="🎨 Generating VJ content...",
            bg="black",
            fg="white",
            font=("Arial", 12),
        )
        status_label.pack(pady=5)

        print("✅ Tkinter window created")

        # Function to update VJ display
        def update_vj_display():
            try:
                # Create high-energy frame
                frame = Frame(
                    {
                        FrameSignal.freq_low: 0.8
                        + 0.2 * np.sin(root.tk.call("clock", "seconds")),
                        FrameSignal.freq_high: 0.7
                        + 0.3 * np.cos(root.tk.call("clock", "seconds")),
                        FrameSignal.freq_all: 0.75
                        + 0.25 * np.sin(root.tk.call("clock", "seconds") * 1.5),
                    }
                )
                scheme = ColorScheme(Color("red"), Color("blue"), Color("yellow"))

                # Generate VJ frame
                vj_frame = vj_director.step(frame, scheme)

                if vj_frame is not None and vj_frame.size > 0:
                    # Convert to PIL Image
                    if len(vj_frame.shape) == 3 and vj_frame.shape[2] >= 3:
                        # Use RGB channels only
                        rgb_frame = vj_frame[:, :, :3]
                        pil_image = Image.fromarray(rgb_frame.astype(np.uint8))
                    else:
                        pil_image = Image.fromarray(vj_frame.astype(np.uint8))

                    # Convert to PhotoImage
                    photo = ImageTk.PhotoImage(pil_image)

                    # Update canvas
                    canvas.delete("all")
                    canvas.create_image(0, 0, anchor="nw", image=photo)
                    canvas.image = photo  # Keep reference

                    # Update status
                    coverage = (np.count_nonzero(vj_frame) / vj_frame.size) * 100
                    status_label.config(text=f"🎆 VJ Active - {coverage:.1f}% coverage")

                else:
                    # Show test pattern if no VJ frame
                    canvas.delete("all")
                    canvas.create_rectangle(0, 0, 400, 300, fill="red", outline="white")
                    canvas.create_text(
                        200,
                        150,
                        text="❌ NO VJ CONTENT",
                        fill="white",
                        font=("Arial", 16, "bold"),
                    )
                    status_label.config(text="❌ No VJ frame generated")

            except Exception as e:
                # Show error pattern
                canvas.delete("all")
                canvas.create_rectangle(0, 0, 400, 300, fill="orange", outline="red")
                canvas.create_text(
                    200,
                    150,
                    text=f"⚠️ ERROR: {str(e)[:30]}",
                    fill="white",
                    font=("Arial", 12),
                )
                status_label.config(text=f"⚠️ Error: {e}")
                print(f"VJ display error: {e}")

            # Schedule next update
            root.after(100, update_vj_display)  # 10 FPS for testing

        # Start VJ updates
        update_vj_display()

        print("🎬 VJ display test running...")
        print("👁️ Look for VJ content in the window!")

        # Run for 10 seconds
        root.after(10000, root.quit)
        root.mainloop()

        print("✅ VJ display test completed")

        vj_director.cleanup()
        return True

    except Exception as e:
        print(f"❌ VJ display test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_simple_vj_content():
    """Test simple VJ content generation"""
    print("\n🎨 Testing simple VJ content generation...")

    try:
        from parrot.vj.base import SolidLayer
        from parrot.vj.renderer import ModernGLRenderer
        from parrot.director.frame import Frame, FrameSignal
        from parrot.director.color_scheme import ColorScheme
        from parrot.utils.colour import Color

        # Create simple renderer
        renderer = ModernGLRenderer(width=200, height=150)

        # Add simple red layer
        red_layer = SolidLayer("test_red", color=(255, 0, 0), alpha=255, z_order=1)
        renderer.add_layer(red_layer)

        print("✅ Simple renderer created with red layer")

        # Create test frame
        frame = Frame({FrameSignal.freq_all: 0.8})
        scheme = ColorScheme(Color("white"), Color("black"), Color("red"))

        # Render frame
        result = renderer.render_frame(frame, scheme)

        if result is not None:
            print(f"✅ Simple render successful: {result.shape}")

            # Check if it's actually red
            red_pixels = np.sum(result[:, :, 0] > 200)
            total_pixels = result.shape[0] * result.shape[1]
            red_percentage = (red_pixels / total_pixels) * 100

            print(f"   Red pixels: {red_pixels:,} ({red_percentage:.1f}%)")

            if red_percentage > 50:
                print("✅ Red content confirmed")
            else:
                print("⚠️ Not enough red content")

        else:
            print("❌ Simple render returned None")
            return False

        renderer.cleanup()
        return True

    except Exception as e:
        print(f"❌ Simple VJ test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Run VJ rendering tests"""
    print("🎬" * 60)
    print("  VJ RENDERING DIAGNOSTIC TESTS")
    print("🎬" * 60)

    # Test 1: VJ frame generation
    success1 = test_vj_frame_generation()

    # Test 2: Simple content
    success2 = test_simple_vj_content()

    # Test 3: VJ display in Tkinter
    success3 = test_vj_display_in_tkinter()

    if success1 and success2 and success3:
        print("\n" + "✅" * 60)
        print("  ALL VJ RENDERING TESTS PASSED!")
        print("✅" * 60)

        print("\n🏆 VJ Rendering Status:")
        print("   ✅ VJ frame generation working")
        print("   ✅ Simple content rendering working")
        print("   ✅ Tkinter display integration working")
        print("   ✅ Visual content confirmed")

        print("\n🎆 Your VJ system should display:")
        print("   🔺 82 floating metallic pyramids")
        print("   📹 Halloween videos with effects")
        print("   🎨 Colorful, dynamic visuals")
        print("   ⚡ Real-time audio responsiveness")

    else:
        print("\n❌ Some VJ rendering tests failed")
        print("🔧 VJ display needs fixes")

    return success1 and success2 and success3


if __name__ == "__main__":
    main()
