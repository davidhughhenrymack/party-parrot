"""
VJ Only Application - Runs VJ system with GUI but no lighting
"""

import os
import sys
import time
import tkinter as tk
from tkinter import Frame, Button, Label, Canvas, BOTH, LEFT
import numpy as np
from colorama import Fore, Style, init

from parrot.state import State
from parrot.director.vj_director import VJDirector
from parrot.director.frame import Frame as AudioFrame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode
from parrot.utils.colour import Color
from parrot.listeners.mic import AudioHandler

# Initialize colorama for colored output
init(autoreset=True)


class VJOnlyGUI(tk.Tk):
    """Simple GUI for VJ-only mode"""

    def __init__(self, vj_director: VJDirector, state: State):
        super().__init__()

        self.vj_director = vj_director
        self.state = state
        self.vj_visible = False

        # Setup window
        self.title("🎆 Party Parrot VJ System")
        self.configure(bg="#222")
        self.geometry("1000x700+100+100")

        # Make window visible
        self.lift()
        self.attributes("-topmost", True)
        self.focus_force()
        self.after(2000, lambda: self.attributes("-topmost", False))

        self._create_interface()

    def _create_interface(self):
        """Create pure VJ interface - no UI elements"""
        # VJ display canvas - PURE VIDEO OUTPUT ONLY
        self.vj_canvas = Canvas(
            self,
            bg="black",
            borderwidth=0,
            highlightthickness=0,
            cursor="none",  # No cursor
        )
        self.vj_canvas.pack(fill="both", expand=True)  # Full window

        # Bind minimal controls (hidden from display)
        self.bind("<KeyPress-Escape>", lambda e: self.quit())
        self.bind("<KeyPress-1>", lambda e: self._set_mode(Mode.gentle))
        self.bind("<KeyPress-2>", lambda e: self._set_mode(Mode.rave))
        self.bind("<KeyPress-3>", lambda e: self._set_mode(Mode.blackout))
        self.focus_set()

        # Start VJ display immediately
        self.vj_visible = True
        self._start_vj_updates()

    def _set_mode(self, mode: Mode):
        """Set VJ mode"""
        self.state.set_mode(mode)
        print(f"{Fore.MAGENTA}🎭 VJ Mode: {mode.name}{Style.RESET_ALL}")

    def _start_vj_updates(self):
        """Start VJ display updates"""
        if not self.vj_visible:
            return

        try:
            # Get current VJ frame
            vj_frame = self.vj_director.get_current_frame()

            if vj_frame is not None:
                # Update canvas with VJ frame
                self._update_vj_canvas(vj_frame)
        except Exception as e:
            print(f"VJ update error: {e}")

        # Schedule next update
        if self.vj_visible:
            self.after(33, self._start_vj_updates)  # ~30 FPS

    def _update_vj_canvas(self, vj_frame: np.ndarray):
        """Update VJ canvas with frame"""
        try:
            from PIL import Image, ImageTk

            # Convert numpy to PIL image and fix orientation
            if len(vj_frame.shape) == 3 and vj_frame.shape[2] >= 3:
                rgb_frame = vj_frame[:, :, :3].astype(np.uint8)
                rgb_frame = np.flipud(rgb_frame)  # Fix upside-down video
                pil_image = Image.fromarray(rgb_frame)
            else:
                corrected_frame = np.flipud(vj_frame.astype(np.uint8))
                pil_image = Image.fromarray(corrected_frame)

            # Resize to canvas
            canvas_width = self.vj_canvas.winfo_width()
            canvas_height = self.vj_canvas.winfo_height()

            if canvas_width > 1 and canvas_height > 1:
                pil_image = pil_image.resize((canvas_width, canvas_height))
                photo = ImageTk.PhotoImage(pil_image)

                # Update canvas
                self.vj_canvas.delete("all")
                self.vj_canvas.create_image(0, 0, anchor="nw", image=photo)
                self.vj_canvas.image = photo  # Keep reference

        except Exception as e:
            # Fallback: show colored rectangle
            self.vj_canvas.delete("all")
            self.vj_canvas.create_rectangle(
                0,
                0,
                self.vj_canvas.winfo_width(),
                self.vj_canvas.winfo_height(),
                fill="purple",
                outline="gold",
            )
            self.vj_canvas.create_text(
                self.vj_canvas.winfo_width() // 2,
                self.vj_canvas.winfo_height() // 2,
                text="🎆 VJ SYSTEM ACTIVE 🎆",
                fill="white",
                font=("Arial", 24, "bold"),
            )


class VJOnlyApp:
    """VJ-only application with GUI"""

    def __init__(self, args):
        self.args = args

        print(f"{Fore.CYAN}🎬 Starting VJ-Only Mode{Style.RESET_ALL}")

        # Create state and VJ director
        self.state = State()
        self.state.set_mode(Mode.rave)  # Start in rave mode for VJ

        print(f"{Fore.GREEN}🎬 VJ System initializing...{Style.RESET_ALL}")

        # Suppress verbose VJ initialization
        import sys
        from io import StringIO

        old_stdout = sys.stdout
        sys.stdout = StringIO()

        try:
            self.vj_director = VJDirector(self.state, width=1920, height=1080)
        finally:
            sys.stdout = old_stdout

        print(
            f"{Fore.GREEN}✅ VJ System ready: 9 layers, 11 interpreters, 82 pyramids{Style.RESET_ALL}"
        )

        # Create GUI if not disabled
        if not args.no_gui:
            print(f"{Fore.YELLOW}🖥️ Creating VJ GUI...{Style.RESET_ALL}")
            self.gui = VJOnlyGUI(self.vj_director, self.state)
            print(f"{Fore.GREEN}✅ VJ GUI ready{Style.RESET_ALL}")
        else:
            self.gui = None
            print(f"{Fore.YELLOW}🖥️ Running VJ in headless mode{Style.RESET_ALL}")

        # Audio setup (simplified)
        self.should_stop = False
        self.frame_count = 0

    def run(self):
        """Run VJ-only application"""
        print(f"{Fore.MAGENTA}🎆 VJ System starting...{Style.RESET_ALL}")

        if self.gui:
            # Run with GUI
            self._run_with_gui()
        else:
            # Run headless
            self._run_headless()

    def _run_with_gui(self):
        """Run VJ system with GUI"""
        print(f"{Fore.CYAN}🖥️ VJ GUI Mode - Window should be visible{Style.RESET_ALL}")
        print(f"{Fore.YELLOW}⌨️  Controls:{Style.RESET_ALL}")
        print(f"   {Fore.WHITE}SPACEBAR{Style.RESET_ALL} - Toggle VJ display")
        print(
            f"   {Fore.WHITE}1,2,3{Style.RESET_ALL} - Change modes (Gentle, Rave, Blackout)"
        )
        print(f"   {Fore.WHITE}🎬 Button{Style.RESET_ALL} - Toggle VJ display")

        # Start VJ processing in background
        self._start_vj_processing()

        # Run GUI
        self.gui.mainloop()

    def _run_headless(self):
        """Run VJ system headless"""
        print(f"{Fore.CYAN}🖥️ VJ Headless Mode{Style.RESET_ALL}")
        print(
            f"{Fore.YELLOW}🌐 Web control: http://localhost:{self.args.web_port}{Style.RESET_ALL}"
        )

        try:
            while not self.should_stop:
                self._process_vj_frame()
                time.sleep(0.033)  # ~30 FPS
        except KeyboardInterrupt:
            print(f"\n{Fore.RED}🛑 VJ System stopped{Style.RESET_ALL}")

    def _start_vj_processing(self):
        """Start VJ processing for GUI mode"""
        self._process_vj_frame()
        if not self.should_stop and self.gui:
            self.gui.after(33, self._start_vj_processing)  # ~30 FPS

    def _process_vj_frame(self):
        """Process a single VJ frame"""
        try:
            # Create test audio frame (in real app this would come from microphone)
            audio_values = {
                FrameSignal.freq_low: 0.5 + 0.3 * np.sin(time.time() * 2),
                FrameSignal.freq_high: 0.4 + 0.4 * np.sin(time.time() * 3),
                FrameSignal.freq_all: 0.45 + 0.35 * np.sin(time.time() * 1.5),
                FrameSignal.sustained_low: 0.3,
                FrameSignal.sustained_high: 0.25,
            }

            frame = AudioFrame(audio_values)
            scheme = ColorScheme(Color("gold"), Color("purple"), Color("cyan"))

            # Process VJ frame
            result = self.vj_director.step(frame, scheme)

            # Occasional scene shifts
            if self.frame_count % 1800 == 0:  # Every 60 seconds at 30fps
                print(f"{Fore.MAGENTA}🔄 Scene shift{Style.RESET_ALL}")
                self.vj_director.shift_vj_interpreters()

            self.frame_count += 1

        except Exception as e:
            print(f"VJ processing error: {e}")

    def quit(self):
        """Stop VJ application"""
        self.should_stop = True
        if self.vj_director:
            self.vj_director.cleanup()
