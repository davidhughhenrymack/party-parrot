#!/usr/bin/env python3
"""
Pure VJ Display Window - No GUI overlays, just video output
"""
import os
import sys
import time
import tkinter as tk
from tkinter import Canvas
import numpy as np
from colorama import Fore, Style

os.environ["TK_SILENCE_DEPRECATION"] = "1"


class PureVJWindow:
    """Pure VJ display window with no GUI overlays"""

    def __init__(self, width=1920, height=1080):
        self.width = width
        self.height = height

        # Create VJ system
        print(f"{Fore.CYAN}🎬 Creating pure VJ display...{Style.RESET_ALL}")

        from parrot.state import State
        from parrot.director.vj_director import VJDirector
        from parrot.director.mode import Mode

        self.state = State()
        self.state.set_mode(Mode.rave)

        # Suppress verbose VJ initialization
        from io import StringIO

        old_stdout = sys.stdout
        sys.stdout = StringIO()

        try:
            self.vj_director = VJDirector(
                self.state, width=self.width, height=self.height
            )
        finally:
            sys.stdout = old_stdout

        print(f"{Fore.GREEN}✅ VJ System ready{Style.RESET_ALL}")

        # Create Tkinter window
        self.root = tk.Tk()
        self.root.title("🎆 Party Parrot VJ")
        self.root.configure(bg="black")
        self.root.geometry(f"{width}x{height}+0+0")

        # Remove window decorations for pure video output
        self.root.overrideredirect(True)  # Remove title bar

        # Make fullscreen-like
        self.root.attributes("-topmost", True)
        self.root.focus_force()

        # Create canvas that fills entire window
        self.canvas = Canvas(
            self.root,
            width=width,
            height=height,
            bg="black",
            borderwidth=0,
            highlightthickness=0,
            cursor="none",  # No cursor
        )
        self.canvas.pack(fill="both", expand=True)

        # Bind keys for control
        self.root.bind("<KeyPress-Escape>", lambda e: self.root.quit())
        self.root.bind("<KeyPress-f>", lambda e: self._toggle_fullscreen())
        self.root.bind("<KeyPress-1>", lambda e: self._set_mode(Mode.gentle))
        self.root.bind("<KeyPress-2>", lambda e: self._set_mode(Mode.rave))
        self.root.bind("<KeyPress-3>", lambda e: self._set_mode(Mode.blackout))

        print(f"{Fore.GREEN}✅ Pure VJ window created{Style.RESET_ALL}")
        print(
            f"{Fore.YELLOW}⌨️  Controls: ESC=quit, F=fullscreen, 1/2/3=modes{Style.RESET_ALL}"
        )

    def _set_mode(self, mode):
        """Set VJ mode"""
        self.state.set_mode(mode)
        print(f"{Fore.MAGENTA}🎭 Mode: {mode.name}{Style.RESET_ALL}")

    def _toggle_fullscreen(self):
        """Toggle fullscreen mode"""
        current = self.root.attributes("-fullscreen")
        self.root.attributes("-fullscreen", not current)

    def _update_display(self):
        """Update VJ display with current frame"""
        try:
            # Create test audio frame
            audio_values = {
                FrameSignal.freq_low: 0.7 + 0.3 * np.sin(time.time() * 2),
                FrameSignal.freq_high: 0.6 + 0.4 * np.sin(time.time() * 3),
                FrameSignal.freq_all: 0.65 + 0.35 * np.sin(time.time() * 1.5),
                FrameSignal.sustained_low: 0.5,
                FrameSignal.sustained_high: 0.4,
            }

            from parrot.director.frame import Frame as AudioFrame
            from parrot.director.color_scheme import ColorScheme
            from parrot.utils.colour import Color

            frame = AudioFrame(audio_values)
            scheme = ColorScheme(Color("red"), Color("blue"), Color("yellow"))

            # Get VJ frame
            vj_frame = self.vj_director.step(frame, scheme)

            if vj_frame is not None and vj_frame.size > 0:
                try:
                    from PIL import Image, ImageTk

                    # Convert to RGB
                    if len(vj_frame.shape) == 3 and vj_frame.shape[2] >= 3:
                        rgb_frame = vj_frame[:, :, :3].astype(np.uint8)
                    else:
                        rgb_frame = vj_frame.astype(np.uint8)

                    # Create PIL image
                    pil_image = Image.fromarray(rgb_frame)

                    # Resize to canvas
                    canvas_width = self.canvas.winfo_width()
                    canvas_height = self.canvas.winfo_height()

                    if canvas_width > 1 and canvas_height > 1:
                        pil_image = pil_image.resize(
                            (canvas_width, canvas_height), Image.LANCZOS
                        )
                        photo = ImageTk.PhotoImage(pil_image)

                        # Display image (no overlays)
                        self.canvas.delete("all")
                        self.canvas.create_image(0, 0, anchor="nw", image=photo)
                        self.canvas.image = photo

                except Exception as e:
                    # Show error with visual feedback
                    self.canvas.delete("all")
                    self.canvas.create_rectangle(
                        0,
                        0,
                        self.canvas.winfo_width(),
                        self.canvas.winfo_height(),
                        fill="red",
                        outline="white",
                    )
                    self.canvas.create_text(
                        self.canvas.winfo_width() // 2,
                        self.canvas.winfo_height() // 2,
                        text=f"VJ RENDER ERROR",
                        fill="white",
                        font=("Arial", 24, "bold"),
                    )
                    print(f"VJ render error: {e}")
            else:
                # Show "no content" pattern
                self.canvas.delete("all")
                self.canvas.create_rectangle(
                    0,
                    0,
                    self.canvas.winfo_width(),
                    self.canvas.winfo_height(),
                    fill="blue",
                    outline="cyan",
                )
                self.canvas.create_text(
                    self.canvas.winfo_width() // 2,
                    self.canvas.winfo_height() // 2,
                    text="🎬 NO VJ CONTENT",
                    fill="white",
                    font=("Arial", 24, "bold"),
                )

        except Exception as e:
            print(f"VJ update error: {e}")

        # Schedule next update
        self.root.after(100, self._update_display)  # 10 FPS

    def run(self):
        """Run the pure VJ display"""
        print(f"{Fore.MAGENTA}🎆 Starting pure VJ display...{Style.RESET_ALL}")

        # Start display updates
        self.root.after(100, self._update_display)

        # Run GUI loop
        self.root.mainloop()

        # Cleanup
        self.vj_director.cleanup()
        print(f"{Fore.GREEN}✅ VJ display closed{Style.RESET_ALL}")


def main():
    """Run pure VJ display"""
    import argparse

    parser = argparse.ArgumentParser(description="Pure VJ Display")
    parser.add_argument("--width", type=int, default=800, help="Display width")
    parser.add_argument("--height", type=int, default=600, help="Display height")
    parser.add_argument("--fullscreen", action="store_true", help="Start in fullscreen")
    args = parser.parse_args()

    print("🎬" * 50)
    print("  PURE VJ DISPLAY")
    print("🎬" * 50)

    try:
        vj_window = PureVJWindow(args.width, args.height)

        if args.fullscreen:
            vj_window.root.attributes("-fullscreen", True)

        vj_window.run()

    except KeyboardInterrupt:
        print(f"\n{Fore.RED}🛑 VJ Display stopped{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}❌ VJ Display failed: {e}{Style.RESET_ALL}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
