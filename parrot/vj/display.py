"""
VJ Display Manager - Abstracts VJ functionality from GUI implementation
"""

import time
from typing import Optional, Callable, Any
import numpy as np
from parrot.director.director import Director
from parrot.state import State

try:
    from PIL import Image, ImageTk

    HAS_PIL = True
except ImportError:
    HAS_PIL = False
    print("Warning: PIL not available. VJ display will be limited.")


class VJDisplayManager:
    """Manages VJ display functionality independently of GUI framework"""

    def __init__(self, state: State, director: Director):
        self.state = state
        self.director = director

        # Display state
        self.is_active = False
        self.current_frame: Optional[np.ndarray] = None

        # Performance tracking
        self.last_update_time = 0.0
        self.frame_count = 0
        self.fps = 0.0

        # Callbacks for GUI integration
        self.on_frame_ready: Optional[Callable[[np.ndarray], None]] = None
        self.on_display_toggle: Optional[Callable[[bool], None]] = None
        self.on_error: Optional[Callable[[str], None]] = None

    def set_active(self, active: bool):
        """Enable or disable VJ display"""
        if self.is_active == active:
            return

        self.is_active = active
        self.state.set_vj_mode(active)

        if self.on_display_toggle:
            self.on_display_toggle(active)

        if active:
            print("VJ Display activated")
        else:
            print("VJ Display deactivated")

    def toggle(self):
        """Toggle VJ display on/off"""
        self.set_active(not self.is_active)

    def update(self):
        """Update VJ display with latest frame from director"""
        if not self.is_active:
            return

        try:
            # Get VJ frame from director
            vj_frame = self.director.get_vj_frame()

            if vj_frame is not None:
                self.current_frame = vj_frame
                self._update_performance_stats()

                # Notify GUI if callback is set
                if self.on_frame_ready:
                    self.on_frame_ready(vj_frame)

        except Exception as e:
            error_msg = f"Error updating VJ display: {e}"
            if self.on_error:
                self.on_error(error_msg)
            else:
                print(error_msg)

    def _update_performance_stats(self):
        """Update performance statistics"""
        current_time = time.time()
        self.frame_count += 1

        # Calculate FPS every second
        if current_time - self.last_update_time >= 1.0:
            self.fps = self.frame_count / (current_time - self.last_update_time)
            self.last_update_time = current_time
            self.frame_count = 0

    def get_current_frame(self) -> Optional[np.ndarray]:
        """Get the current VJ frame"""
        return self.current_frame

    def get_performance_info(self) -> dict:
        """Get performance information"""
        vj_info = self.director.get_vj_info()
        return {
            "display_fps": self.fps,
            "display_active": self.is_active,
            "vj_system": vj_info,
        }

    def convert_frame_for_display(
        self, frame: np.ndarray, target_size: tuple = None
    ) -> Optional[Any]:
        """Convert VJ frame for display in GUI frameworks

        Args:
            frame: RGBA numpy array
            target_size: Optional (width, height) to resize to

        Returns:
            PIL Image or None if conversion fails
        """
        if not HAS_PIL or frame is None:
            return None

        try:
            # Ensure frame is in the right format
            if frame.dtype != np.uint8:
                frame = (frame * 255).astype(np.uint8)

            # Convert RGBA to RGB for display (composite on black background)
            if frame.shape[2] == 4:
                # Create RGB image with black background
                rgb_frame = np.zeros(
                    (frame.shape[0], frame.shape[1], 3), dtype=np.uint8
                )
                alpha = frame[:, :, 3:4] / 255.0
                rgb_frame = (frame[:, :, :3] * alpha).astype(np.uint8)
            else:
                rgb_frame = frame

            # Create PIL image
            pil_image = Image.fromarray(rgb_frame)

            # Resize if requested
            if target_size and target_size[0] > 1 and target_size[1] > 1:
                pil_image = pil_image.resize(target_size, Image.LANCZOS)

            return pil_image

        except Exception as e:
            if self.on_error:
                self.on_error(f"Error converting frame for display: {e}")
            return None

    def create_tkinter_photo(
        self, frame: np.ndarray, target_size: tuple = None
    ) -> Optional["ImageTk.PhotoImage"]:
        """Create a Tkinter PhotoImage from VJ frame"""
        if not HAS_PIL:
            return None

        pil_image = self.convert_frame_for_display(frame, target_size)
        if pil_image is None:
            return None

        try:
            return ImageTk.PhotoImage(pil_image)
        except Exception as e:
            if self.on_error:
                self.on_error(f"Error creating Tkinter photo: {e}")
            return None

    def save_frame(self, filename: str, frame: np.ndarray = None) -> bool:
        """Save current or specified frame to file"""
        if not HAS_PIL:
            return False

        frame_to_save = frame if frame is not None else self.current_frame
        if frame_to_save is None:
            return False

        try:
            pil_image = self.convert_frame_for_display(frame_to_save)
            if pil_image:
                pil_image.save(filename)
                return True
        except Exception as e:
            if self.on_error:
                self.on_error(f"Error saving frame: {e}")

        return False


class VJWindow:
    """Abstract base class for VJ display windows"""

    def __init__(self, display_manager: VJDisplayManager):
        self.display_manager = display_manager
        self.is_visible = False

        # Connect to display manager
        self.display_manager.on_frame_ready = self.update_display
        self.display_manager.on_display_toggle = self.on_display_toggle

    def show(self):
        """Show the VJ window"""
        self.is_visible = True
        self._show_implementation()

    def hide(self):
        """Hide the VJ window"""
        self.is_visible = False
        self._hide_implementation()

    def toggle(self):
        """Toggle window visibility"""
        if self.is_visible:
            self.hide()
        else:
            self.show()

    def update_display(self, frame: np.ndarray):
        """Update display with new frame - override in subclasses"""
        pass

    def on_display_toggle(self, active: bool):
        """Handle display activation/deactivation"""
        if active and not self.is_visible:
            self.show()
        elif not active and self.is_visible:
            self.hide()

    def _show_implementation(self):
        """Platform-specific show implementation - override in subclasses"""
        pass

    def _hide_implementation(self):
        """Platform-specific hide implementation - override in subclasses"""
        pass


class TkinterVJWindow(VJWindow):
    """Tkinter-specific VJ display window"""

    def __init__(self, display_manager: VJDisplayManager, parent_window):
        super().__init__(display_manager)
        self.parent = parent_window
        self.window = None
        self.canvas = None
        self.info_label = None

    def _show_implementation(self):
        """Create and show Tkinter window"""
        if self.window is None:
            self._create_window()

        self.window.deiconify()
        self.window.lift()

    def _hide_implementation(self):
        """Hide Tkinter window"""
        if self.window:
            self.window.withdraw()

    def _create_window(self):
        """Create the Tkinter window with error handling"""
        try:
            from tkinter import Toplevel, Canvas, Label, BOTH

            # Define colors locally
            BG = "#222"

            # Create window with error handling
            self.window = Toplevel(self.parent)
            self.window.title("Party Parrot - VJ Display")
            self.window.configure(bg=BG)
            self.window.geometry("800x600")

            # Handle window close
            self.window.protocol("WM_DELETE_WINDOW", self._on_window_close)

            # Create canvas
            self.canvas = Canvas(
                self.window,
                width=800,
                height=600,
                bg="black",
                borderwidth=0,
                highlightthickness=0,
            )
            self.canvas.pack(fill=BOTH, expand=True)

            # Add info label
            self.info_label = Label(
                self.window,
                text="VJ Display - Press SPACE or ESC to close",
                bg=BG,
                fg="white",
                font=("Arial", 10),
            )
            self.info_label.pack(side="bottom", pady=5)

            # Bind keys
            self.window.bind("<KeyPress-space>", lambda e: self.hide())
            self.window.bind("<KeyPress-Escape>", lambda e: self.hide())
            self.window.focus_set()

        except Exception as e:
            print(f"Failed to create VJ window: {e}")
            self.window = None
            self.canvas = None
            self.info_label = None

    def _on_window_close(self):
        """Handle window close button"""
        self.display_manager.set_active(False)

    def update_display(self, frame: np.ndarray):
        """Update the Tkinter canvas with new frame"""
        if not self.is_visible or not self.canvas:
            return

        try:
            # Get canvas size
            canvas_width = self.canvas.winfo_width()
            canvas_height = self.canvas.winfo_height()

            if canvas_width <= 1 or canvas_height <= 1:
                return

            # Convert frame to PhotoImage
            photo = self.display_manager.create_tkinter_photo(
                frame, (canvas_width, canvas_height)
            )

            if photo:
                # Clear canvas and draw new image
                self.canvas.delete("all")
                self.canvas.create_image(
                    canvas_width // 2, canvas_height // 2, image=photo, anchor="center"
                )

                # Keep reference to prevent garbage collection
                self.canvas.image = photo

        except Exception as e:
            print(f"Error updating Tkinter VJ display: {e}")

    def cleanup(self):
        """Clean up the window"""
        if self.window:
            try:
                self.window.destroy()
            except:
                pass
            self.window = None
