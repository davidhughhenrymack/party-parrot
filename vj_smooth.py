#!/usr/bin/env python3
"""
Butter Smooth VJ System - Optimized for 60 FPS
Uses performance mode with reduced effects for smooth operation
"""
import os
import time
import tkinter as tk
from tkinter import Canvas, Label, Frame as TkFrame, Button, LEFT
import numpy as np
from colorama import Fore, Style, init

os.environ["TK_SILENCE_DEPRECATION"] = "1"
init(autoreset=True)


class SmoothVJWindow:
    """Butter smooth VJ window optimized for high frame rates"""

    def __init__(self, width=1280, height=720):
        self.width = width
        self.height = height
        self.frame_count = 0
        self.last_fps_time = time.time()
        self.fps = 0

        print(f"{Fore.CYAN}🚀 Creating smooth VJ system...{Style.RESET_ALL}")

        # Create optimized VJ system
        from parrot.state import State
        from parrot.director.mode import Mode
        from parrot.vj.performance_mode import create_performance_vj_renderer
        from parrot.interpreters.base import InterpreterArgs

        # Store Mode for later use
        self.Mode = Mode

        self.state = State()
        self.state.set_mode(Mode.rave)

        # Create performance-optimized renderer
        args = InterpreterArgs(hype=70, allow_rainbows=True, min_hype=0, max_hype=100)
        self.vj_renderer = create_performance_vj_renderer(
            Mode.rave, args, width, height
        )

        print(f"{Fore.GREEN}✅ Smooth VJ system ready{Style.RESET_ALL}")

        # Create GUI
        self.root = tk.Tk()
        self.root.title("🚀 Butter Smooth VJ")
        self.root.configure(bg="#111")
        self.root.geometry(f"{width + 200}x{height + 100}+50+50")

        # Make window visible
        self.root.lift()
        self.root.attributes("-topmost", True)
        self.root.focus_force()
        self.root.after(2000, lambda: self.root.attributes("-topmost", False))

        self._create_interface()

    def _create_interface(self):
        """Create smooth VJ interface"""
        # Control frame
        control_frame = TkFrame(self.root, bg="#111")
        control_frame.pack(fill="x", padx=5, pady=5)

        # FPS display
        self.fps_label = Label(
            control_frame,
            text="🚀 FPS: --",
            bg="#111",
            fg="#00ff00",
            font=("Arial", 14, "bold"),
        )
        self.fps_label.pack(side=LEFT, padx=10)

        # Mode buttons
        for mode, color in [
            (self.Mode.gentle, "#4444ff"),
            (self.Mode.rave, "#ff4444"),
            (self.Mode.blackout, "#444444"),
        ]:
            btn = Button(
                control_frame,
                text=mode.name.capitalize(),
                command=lambda m=mode: self._set_mode(m),
                bg=color,
                fg="white",
                font=("Arial", 10, "bold"),
            )
            btn.pack(side=LEFT, padx=2)

        # Performance info
        self.perf_label = Label(
            control_frame,
            text="⚡ Optimized for M4 Max",
            bg="#111",
            fg="#ffaa00",
            font=("Arial", 10),
        )
        self.perf_label.pack(side=LEFT, padx=10)

        # VJ display canvas
        self.canvas = Canvas(
            self.root,
            width=self.width,
            height=self.height,
            bg="black",
            borderwidth=0,
            highlightthickness=0,
            cursor="none",
        )
        self.canvas.pack(padx=10, pady=5)

        # Bind controls
        self.root.bind("<KeyPress-Escape>", lambda e: self.root.quit())
        self.root.bind("<KeyPress-1>", lambda e: self._set_mode(self.Mode.gentle))
        self.root.bind("<KeyPress-2>", lambda e: self._set_mode(self.Mode.rave))
        self.root.bind("<KeyPress-3>", lambda e: self._set_mode(self.Mode.blackout))
        self.root.focus_set()

    def _set_mode(self, mode):
        """Set VJ mode and update performance settings"""
        self.state.set_mode(mode)

        # Recreate renderer for new mode
        from parrot.vj.performance_mode import create_performance_vj_renderer
        from parrot.interpreters.base import InterpreterArgs

        args = InterpreterArgs(hype=70, allow_rainbows=True, min_hype=0, max_hype=100)

        # Cleanup old renderer
        if self.vj_renderer:
            self.vj_renderer.cleanup()

        # Create new optimized renderer
        self.vj_renderer = create_performance_vj_renderer(
            mode, args, self.width, self.height
        )

        print(f"{Fore.MAGENTA}🎭 Mode: {mode.name} (optimized){Style.RESET_ALL}")

    def _update_display(self):
        """Update VJ display with performance monitoring"""
        frame_start = time.perf_counter()

        try:
            # Create dynamic audio frame
            t = time.time()
            audio_values = {
                FrameSignal.freq_low: 0.6 + 0.4 * np.sin(t * 2),
                FrameSignal.freq_high: 0.5 + 0.5 * np.cos(t * 3),
                FrameSignal.freq_all: 0.55 + 0.45 * np.sin(t * 1.5),
                FrameSignal.sustained_low: 0.4,
                FrameSignal.sustained_high: 0.3,
            }

            from parrot.director.frame import Frame as AudioFrame, FrameSignal
            from parrot.director.color_scheme import ColorScheme
            from parrot.utils.colour import Color

            frame = AudioFrame(audio_values)
            scheme = ColorScheme(Color("red"), Color("gold"), Color("cyan"))

            # Render VJ frame
            vj_frame = self.vj_renderer.render_frame(frame, scheme)

            if vj_frame is not None and vj_frame.size > 0:
                try:
                    from PIL import Image, ImageTk

                    # Convert to RGB efficiently
                    rgb_frame = vj_frame[:, :, :3].astype(np.uint8)
                    pil_image = Image.fromarray(rgb_frame)

                    # Resize efficiently
                    canvas_width = self.canvas.winfo_width()
                    canvas_height = self.canvas.winfo_height()

                    if canvas_width > 1 and canvas_height > 1:
                        pil_image = pil_image.resize(
                            (canvas_width, canvas_height), Image.NEAREST
                        )  # Faster resize
                        photo = ImageTk.PhotoImage(pil_image)

                        # Update canvas
                        self.canvas.delete("all")
                        self.canvas.create_image(0, 0, anchor="nw", image=photo)
                        self.canvas.image = photo

                except Exception as e:
                    # Simple error display
                    self.canvas.delete("all")
                    self.canvas.create_rectangle(
                        0, 0, self.width, self.height, fill="red"
                    )

            else:
                # Simple test pattern
                self.canvas.delete("all")
                self.canvas.create_rectangle(0, 0, self.width, self.height, fill="blue")

        except Exception as e:
            print(f"VJ error: {e}")

        # Calculate FPS
        frame_end = time.perf_counter()
        frame_time = frame_end - frame_start
        self.frame_count += 1

        # Update FPS every second
        if frame_end - self.last_fps_time >= 1.0:
            self.fps = self.frame_count / (frame_end - self.last_fps_time)
            self.fps_label.config(text=f"🚀 FPS: {self.fps:.1f}")

            # Performance feedback
            if self.fps >= 50:
                self.fps_label.config(fg="#00ff00")  # Green for excellent
            elif self.fps >= 30:
                self.fps_label.config(fg="#ffff00")  # Yellow for good
            else:
                self.fps_label.config(fg="#ff0000")  # Red for poor

            self.frame_count = 0
            self.last_fps_time = frame_end

        # Schedule next update - target 60 FPS
        target_fps = 60
        target_frame_time = 1.0 / target_fps
        sleep_time = max(1, int((target_frame_time - frame_time) * 1000))

        self.root.after(sleep_time, self._update_display)

    def run(self):
        """Run smooth VJ system"""
        print(f"{Fore.MAGENTA}🚀 Starting butter smooth VJ...{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}⌨️  Controls: ESC=quit, 1/2/3=modes{Style.RESET_ALL}")
        print(f"{Fore.GREEN}🎯 Target: 60 FPS smooth operation{Style.RESET_ALL}")

        # Start display updates
        self.root.after(16, self._update_display)  # Start at 60 FPS

        # Run GUI
        self.root.mainloop()

        # Cleanup
        if self.vj_renderer:
            self.vj_renderer.cleanup()

        print(f"{Fore.GREEN}✅ Smooth VJ closed{Style.RESET_ALL}")


def main():
    """Run butter smooth VJ system"""
    import argparse

    parser = argparse.ArgumentParser(description="Butter Smooth VJ System")
    parser.add_argument("--width", type=int, default=1280, help="Display width")
    parser.add_argument("--height", type=int, default=720, help="Display height")
    parser.add_argument("--fullhd", action="store_true", help="Use 1920x1080")
    args = parser.parse_args()

    if args.fullhd:
        width, height = 1920, 1080
    else:
        width, height = args.width, args.height

    print("🚀" * 50)
    print("  BUTTER SMOOTH VJ SYSTEM")
    print("🚀" * 50)

    print(f"\n🎯 Performance Optimizations:")
    print(f"   Resolution: {width}x{height}")
    print(f"   Target FPS: 60")
    print(f"   Pyramid count: Reduced for performance")
    print(f"   Interpreter count: Minimal for speed")
    print(f"   GPU: M4 Max Metal 3 acceleration")

    try:
        vj_window = SmoothVJWindow(width, height)
        vj_window.run()

    except KeyboardInterrupt:
        print(f"\n{Fore.RED}🛑 Smooth VJ stopped{Style.RESET_ALL}")
    except Exception as e:
        print(f"\n{Fore.RED}❌ Smooth VJ failed: {e}{Style.RESET_ALL}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
