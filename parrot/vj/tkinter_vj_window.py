#!/usr/bin/env python3

import tkinter as tk
from tkinter import Toplevel, Frame, Label, Canvas
import moderngl as mgl
import numpy as np
from beartype import beartype
import time
from typing import Optional
from PIL import Image, ImageTk

from parrot.director.frame import Frame as DirectorFrame
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode


@beartype
class VJRenderer:
    """ModernGL VJ renderer using offscreen rendering (like the cube demo)"""

    def __init__(self, vj_director, width: int = 800, height: int = 600):
        self.vj_director = vj_director
        self.width = width
        self.height = height
        self.ctx = None
        self.fbo = None
        self.running = False

        # Frame data for rendering
        self._latest_frame: Optional[DirectorFrame] = None
        self._latest_scheme: Optional[ColorScheme] = None

        # Initialize ModernGL
        self._init_moderngl()

    def _init_moderngl(self) -> bool:
        """Initialize ModernGL with offscreen rendering"""
        try:
            # Create standalone ModernGL context (like cube demo)
            self.ctx = mgl.create_context(standalone=True)

            # Setup VJ director with ModernGL context
            if self.vj_director:
                self.vj_director.setup(self.ctx)

            return True

        except Exception as e:
            print(f"❌ Failed to initialize VJ ModernGL: {e}")
            import traceback

            traceback.print_exc()
            return False

    def render_frame(self) -> Optional[bytes]:
        """Render a VJ frame and return the image data"""
        if not self.ctx or not self.vj_director:
            return None

        if not self._latest_frame or not self._latest_scheme:
            return None

        try:
            # Get rendered framebuffer from VJ director
            rendered_fbo = self.vj_director.render(
                self.ctx, self._latest_frame, self._latest_scheme
            )

            if rendered_fbo and rendered_fbo.color_attachments:
                # Read the framebuffer data
                texture = rendered_fbo.color_attachments[0]
                image_data = texture.read()
                return image_data

        except Exception as e:
            print(f"VJ render error: {e}")

        return None

    def update_frame_data(self, frame: DirectorFrame, scheme: ColorScheme):
        """Update frame data for rendering (thread-safe)"""
        self._latest_frame = frame
        self._latest_scheme = scheme

    def shift_scene(self):
        """Shift scene using current system mode"""
        if self.vj_director:
            current_mode = self.vj_director.get_current_mode()
            print(f"VJ Scene shift with current mode: {current_mode}")
            self.vj_director.shift_current_mode()
        else:
            print("VJ Director not available for scene shift")

    def cleanup(self):
        """Clean up resources"""
        if self.vj_director:
            self.vj_director.cleanup()


@beartype
class VJFrame(tk.Frame):
    """Tkinter frame that displays VJ rendered content (like ModernGLFrame in cube demo)"""

    def __init__(self, parent, vj_director, **kwargs):
        super().__init__(parent, **kwargs)

        # Create canvas that fills the entire frame
        self.canvas = Canvas(self, bg="black", highlightthickness=0)
        self.canvas.pack(fill=tk.BOTH, expand=True)

        # Create VJ renderer
        self.vj_renderer = VJRenderer(vj_director, 800, 600)
        self.running = False

        # Check if ModernGL initialized successfully
        if self.vj_renderer.ctx is None:
            self._show_error()

    def _show_error(self):
        """Show error message if ModernGL failed"""
        self.canvas.create_text(
            400,
            300,
            text="❌ VJ ModernGL initialization failed!\nCheck console for details.",
            fill="red",
            font=("Arial", 16),
            justify=tk.CENTER,
        )

    def start_animation(self):
        """Start the VJ animation"""
        if self.vj_renderer.ctx is None:
            print("❌ Cannot start VJ animation - ModernGL not initialized")
            return

        self.running = True
        self.vj_renderer.running = True
        self._animate()

    def stop_animation(self):
        """Stop the animation"""
        print("⏹️ Stopping VJ ModernGL animation")
        self.running = False
        self.vj_renderer.running = False

    def _animate(self):
        """Animation loop (like cube demo)"""
        if not self.running or self.vj_renderer.ctx is None:
            return

        try:
            # Render VJ frame
            image_data = self.vj_renderer.render_frame()

            if image_data:
                # Get current canvas size
                canvas_width = self.canvas.winfo_width()
                canvas_height = self.canvas.winfo_height()

                if canvas_width > 1 and canvas_height > 1:
                    # Convert to PIL Image
                    # VJ director returns RGB data, need to determine format and flip if needed
                    try:
                        # Try RGB first (most common for VJ content)
                        image_array = np.frombuffer(image_data, dtype=np.uint8)

                        # Determine the format based on data size
                        total_pixels = len(image_array)

                        # Common VJ output sizes to try
                        common_sizes = [
                            (1920, 1080),  # Full HD
                            (1280, 720),  # HD
                            (800, 600),  # VJ renderer default
                            (canvas_width, canvas_height),  # Canvas size
                        ]

                        pil_image = None
                        for width, height in common_sizes:
                            expected_rgb = width * height * 3
                            expected_rgba = width * height * 4

                            if total_pixels == expected_rgba:
                                # RGBA format
                                image_array = image_array.reshape((height, width, 4))
                                pil_image = Image.fromarray(image_array, "RGBA")
                                break
                            elif total_pixels == expected_rgb:
                                # RGB format
                                image_array = image_array.reshape((height, width, 3))
                                pil_image = Image.fromarray(image_array, "RGB")
                                break

                        if pil_image is None:
                            # Try to guess the dimensions (assume RGB format)
                            if total_pixels % 3 == 0:
                                pixel_count = total_pixels // 3
                                # Try to find reasonable dimensions
                                import math

                                sqrt_pixels = int(math.sqrt(pixel_count))
                                for aspect_ratio in [(16, 9), (4, 3), (1, 1)]:
                                    w = int(
                                        sqrt_pixels
                                        * aspect_ratio[0]
                                        / math.sqrt(
                                            aspect_ratio[0] ** 2 + aspect_ratio[1] ** 2
                                        )
                                    )
                                    h = int(
                                        sqrt_pixels
                                        * aspect_ratio[1]
                                        / math.sqrt(
                                            aspect_ratio[0] ** 2 + aspect_ratio[1] ** 2
                                        )
                                    )
                                    if w * h * 3 == total_pixels:
                                        image_array = image_array.reshape((h, w, 3))
                                        pil_image = Image.fromarray(image_array, "RGB")
                                        print(f"VJ: Detected {w}x{h} RGB format")
                                        break

                        if pil_image is None:
                            print(
                                f"Could not determine VJ image format for {total_pixels} bytes"
                            )
                            return

                        # Scale to fit canvas while maintaining aspect ratio
                        img_width, img_height = pil_image.size
                        img_ratio = img_width / img_height
                        canvas_ratio = canvas_width / canvas_height

                        if img_ratio > canvas_ratio:
                            # Image is wider, fit to width
                            new_width = canvas_width
                            new_height = int(canvas_width / img_ratio)
                        else:
                            # Image is taller, fit to height
                            new_height = canvas_height
                            new_width = int(canvas_height * img_ratio)

                        pil_image = pil_image.resize(
                            (new_width, new_height), Image.LANCZOS
                        )

                        # Convert to PhotoImage for Tkinter
                        photo = ImageTk.PhotoImage(pil_image)

                        # Update canvas
                        self.canvas.delete("all")
                        x = canvas_width // 2
                        y = canvas_height // 2
                        self.canvas.create_image(x, y, image=photo, anchor=tk.CENTER)

                        # Keep a reference to prevent garbage collection
                        self.canvas.image = photo

                    except Exception as e:
                        print(f"Error processing VJ image: {e}")

            # Schedule next frame (60 FPS)
            self.after(16, self._animate)

        except Exception as e:
            print(f"❌ VJ Animation error: {e}")
            import traceback

            traceback.print_exc()
            self.stop_animation()

    def update_frame_data(self, frame: DirectorFrame, scheme: ColorScheme):
        """Update frame data for rendering"""
        if self.vj_renderer:
            self.vj_renderer.update_frame_data(frame, scheme)

    def shift_scene(self):
        """Shift scene"""
        if self.vj_renderer:
            self.vj_renderer.shift_scene()


@beartype
class TkinterVJWindow(Toplevel):
    """Tkinter window that displays VJ content using offscreen ModernGL rendering"""

    def __init__(
        self, parent, vj_director, width: int = 1920, height: int = 1080, **kwargs
    ):
        super().__init__(parent, **kwargs)

        self.vj_director = vj_director
        self.width = width
        self.height = height

        # Window setup - keep title bar but clean interior
        self.title("Party Parrot VJ - Concert Stage")
        self.geometry(f"{width}x{height}")
        self.configure(bg="#000000")

        # Make window resizable
        self.resizable(True, True)

        # Setup the window
        self._setup_window()

        # Handle window close
        self.protocol("WM_DELETE_WINDOW", self._on_closing)

        # Bind keyboard events
        self.bind("<KeyPress>", self._on_key_press)
        self.focus_set()  # Allow window to receive key events

    def _setup_window(self):
        """Setup the window UI"""
        # Create the VJ frame that fills the entire window (no decorations)
        self.vj_frame = VJFrame(self, self.vj_director, bg="#000000")
        self.vj_frame.pack(fill=tk.BOTH, expand=True)

        # Check if VJ frame initialized successfully and start animation
        if self.vj_frame.vj_renderer.ctx is not None:
            # Start the animation
            self.vj_frame.start_animation()
        else:
            print("VJ: ModernGL Initialization Failed")

    def _on_key_press(self, event):
        """Handle keyboard events"""
        if event.keysym == "space":
            self.shift_scene()
        elif event.keysym == "Escape":
            self._on_closing()

    def update_frame_data(self, frame: DirectorFrame, scheme: ColorScheme):
        """Update frame data for rendering (thread-safe)"""
        if self.vj_frame:
            self.vj_frame.update_frame_data(frame, scheme)

    def shift_scene(self):
        """Shift scene using current system mode"""
        if self.vj_frame:
            self.vj_frame.shift_scene()
            print("VJ: Scene shifted")
        else:
            print("VJ Frame not available for scene shift")

    def _on_closing(self):
        """Handle window closing"""
        self.cleanup()
        self.destroy()

    def cleanup(self):
        """Clean up resources"""
        if self.vj_frame:
            self.vj_frame.stop_animation()
            if self.vj_frame.vj_renderer:
                self.vj_frame.vj_renderer.cleanup()


@beartype
class TkinterVJManager:
    """Manager for Tkinter VJ window integration"""

    def __init__(self, vj_director):
        self.vj_director = vj_director
        self.window: Optional[TkinterVJWindow] = None

    def create_window(
        self, parent, width: int = 1920, height: int = 1080, fullscreen: bool = False
    ) -> TkinterVJWindow:
        """Create the Tkinter VJ window"""
        self.window = TkinterVJWindow(
            parent, self.vj_director, width=width, height=height
        )

        if fullscreen:
            self.window.attributes("-fullscreen", True)

        return self.window

    def update_frame_data(self, frame: DirectorFrame, scheme: ColorScheme):
        """Update frame data if window exists"""
        if self.window:
            self.window.update_frame_data(frame, scheme)

    def shift_scene(self):
        """Shift scene if window exists"""
        if self.window:
            self.window.shift_scene()

    def cleanup(self):
        """Clean up resources"""
        if self.window:
            self.window.cleanup()

    def is_window_open(self) -> bool:
        """Check if window is open"""
        return self.window is not None and self.window.winfo_exists()
