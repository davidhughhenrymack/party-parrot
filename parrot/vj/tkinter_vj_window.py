#!/usr/bin/env python3

import tkinter as tk
from tkinter import Toplevel, Frame, Label, Canvas
import moderngl as mgl
import numpy as np
from beartype import beartype
import time
from typing import Optional, Tuple
from PIL import Image, ImageTk

from parrot.director.frame import Frame as DirectorFrame
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode
from parrot.vj.profiler import vj_profiler


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

        # GPU-accelerated display pipeline
        self.display_framebuffer = None
        self.display_shader = None
        self.display_quad_vao = None
        self.current_display_size = (width, height)

        # Initialize ModernGL
        self._init_moderngl()

    def _init_moderngl(self) -> bool:
        """Initialize ModernGL with offscreen rendering"""
        try:
            # Create standalone ModernGL context (like cube demo)
            self.ctx = mgl.create_context(standalone=True)

            self._log_context_device()

            # Setup VJ director with ModernGL context
            if self.vj_director:
                self.vj_director.setup(self.ctx)

            # Setup GPU-accelerated display pipeline
            self._setup_display_pipeline()

            return True

        except Exception as e:
            print(f"❌ Failed to initialize VJ ModernGL: {e}")
            import traceback

            traceback.print_exc()
            return False

    def _log_context_device(self) -> None:
        """Log whether the ModernGL context is using GPU acceleration"""
        if not self.ctx:
            return

        info = self.ctx.info
        vendor = info.get("GL_VENDOR", "unknown")
        renderer = info.get("GL_RENDERER", "unknown")

        # Simple heuristic: software renderers often include these substrings
        software_markers = ("llvmpipe", "softpipe", "mesa", "software", "swiftshader")
        renderer_lower = renderer.lower()
        vendor_lower = vendor.lower()

        is_software = any(
            marker in renderer_lower for marker in software_markers
        ) or any(marker in vendor_lower for marker in software_markers)

        if is_software:
            print(f"🟠 VJ Renderer running on CPU fallback: {renderer} ({vendor})")
        else:
            print(f"🟢 VJ Renderer using GPU: {renderer} ({vendor})")

    def _setup_display_pipeline(self):
        """Setup GPU-accelerated display pipeline for efficient scaling and format conversion"""
        if not self.ctx:
            return

        # Create display shader for GPU-accelerated scaling
        vertex_shader = """
        #version 330 core
        in vec2 in_position;
        in vec2 in_texcoord;
        out vec2 uv;
        
        void main() {
            gl_Position = vec4(in_position, 0.0, 1.0);
            uv = in_texcoord;
        }
        """

        fragment_shader = """
        #version 330 core
        in vec2 uv;
        out vec3 color;
        uniform sampler2D source_texture;
        
        void main() {
            color = texture(source_texture, uv).rgb;
        }
        """

        self.display_shader = self.ctx.program(
            vertex_shader=vertex_shader, fragment_shader=fragment_shader
        )

        # Create fullscreen quad for display scaling
        vertices = np.array(
            [
                # Position  # TexCoord
                -1.0,
                -1.0,
                0.0,
                0.0,  # Bottom-left
                1.0,
                -1.0,
                1.0,
                0.0,  # Bottom-right
                -1.0,
                1.0,
                0.0,
                1.0,  # Top-left
                1.0,
                1.0,
                1.0,
                1.0,  # Top-right
            ],
            dtype=np.float32,
        )

        vbo = self.ctx.buffer(vertices.tobytes())
        self.display_quad_vao = self.ctx.vertex_array(
            self.display_shader, [(vbo, "2f 2f", "in_position", "in_texcoord")]
        )

    def update_display_size(self, width: int, height: int):
        """Update display framebuffer size for GPU-accelerated scaling"""
        if (width, height) != self.current_display_size:
            self.current_display_size = (width, height)

            # Release old framebuffer
            if self.display_framebuffer:
                self.display_framebuffer.release()

            # Create new display framebuffer at target size
            if self.ctx and width > 0 and height > 0:
                display_texture = self.ctx.texture((width, height), 3)
                self.display_framebuffer = self.ctx.framebuffer(
                    color_attachments=[display_texture]
                )

    def render_frame(
        self, canvas_width: int = None, canvas_height: int = None
    ) -> Optional[Tuple[bytes, int, int]]:
        """Render a VJ frame with GPU-accelerated scaling and return the image data"""
        if not self.ctx or not self.vj_director:
            return None

        with vj_profiler.profile("vj_renderer_frame"):
            # Get latest frame data from VJ director
            frame, scheme = self.vj_director.get_latest_frame_data()
            if not frame or not scheme:
                return None

            try:
                # Get rendered framebuffer from VJ director
                with vj_profiler.profile("vj_render_to_fbo"):
                    rendered_fbo = self.vj_director.render(self.ctx, frame, scheme)

                if rendered_fbo and rendered_fbo.color_attachments:
                    source_texture = rendered_fbo.color_attachments[0]
                    source_width, source_height = source_texture.size

                    # Use GPU-accelerated scaling if canvas size is provided and different
                    if (
                        canvas_width
                        and canvas_height
                        and self.display_shader
                        and self.display_quad_vao
                        and (
                            canvas_width != source_width
                            or canvas_height != source_height
                        )
                    ):

                        with vj_profiler.profile("vj_gpu_scale"):
                            # Update display framebuffer size if needed
                            self.update_display_size(canvas_width, canvas_height)

                            if self.display_framebuffer:
                                # Render scaled version using GPU
                                self.display_framebuffer.use()
                                self.ctx.clear(0.0, 0.0, 0.0)

                                # Bind source texture
                                source_texture.use(0)
                                self.display_shader["source_texture"] = 0

                                # Render scaled quad
                                self.display_quad_vao.render(mgl.TRIANGLE_STRIP)

                                # Read from scaled framebuffer
                                with vj_profiler.profile("vj_fbo_read"):
                                    scaled_texture = (
                                        self.display_framebuffer.color_attachments[0]
                                    )
                                    width, height = scaled_texture.size
                                    image_data = scaled_texture.read()
                                return image_data, width, height

                    # Fallback: read original framebuffer data
                    with vj_profiler.profile("vj_fbo_read"):
                        width, height = source_texture.size
                        image_data = source_texture.read()
                    return image_data, width, height

            except Exception as e:
                print(f"VJ render error: {e}")

            return None

    def shift_scene(self):
        """Shift scene using current system mode"""
        if self.vj_director:
            current_mode = self.vj_director.get_current_mode()
            self.vj_director.shift_current_mode()

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
        self.running = False
        self.vj_renderer.running = False

    def _animate(self):
        """Animation loop (like cube demo)"""
        if not self.running or self.vj_renderer.ctx is None:
            return

        try:
            with vj_profiler.profile("vj_animate_loop"):
                # Get current canvas size for GPU-accelerated scaling
                canvas_width = self.canvas.winfo_width()
                canvas_height = self.canvas.winfo_height()

                # Render VJ frame with GPU scaling if canvas is valid
                if canvas_width > 1 and canvas_height > 1:
                    image_result = self.vj_renderer.render_frame(
                        canvas_width, canvas_height
                    )
                else:
                    image_result = self.vj_renderer.render_frame()

                if image_result:
                    image_data, render_width, render_height = image_result

                    if canvas_width > 1 and canvas_height > 1:
                        # Convert to PIL Image - GPU-accelerated path
                        with vj_profiler.profile("vj_image_processing"):
                            try:
                                # Fast path: GPU has already scaled to correct size
                                expected_rgb = render_width * render_height * 3
                                expected_rgba = render_width * render_height * 4

                                if len(image_data) == expected_rgb:
                                    # RGB format - most common case
                                    image_array = np.frombuffer(
                                        image_data, dtype=np.uint8
                                    ).reshape((render_height, render_width, 3))
                                    pil_image = Image.fromarray(image_array, "RGB")
                                elif len(image_data) == expected_rgba:
                                    # RGBA format
                                    image_array = np.frombuffer(
                                        image_data, dtype=np.uint8
                                    ).reshape((render_height, render_width, 4))
                                    pil_image = Image.fromarray(image_array, "RGBA")
                                else:
                                    print(
                                        f"Unexpected VJ image size: {len(image_data)} bytes for {render_width}x{render_height}"
                                    )
                                    return

                                # GPU scaling means we can skip CPU resize in most cases
                                with vj_profiler.profile("vj_image_resize"):
                                    img_width, img_height = pil_image.size

                                    # Only resize if GPU scaling wasn't used or size mismatch is significant
                                    if (
                                        abs(img_width - canvas_width) > 10
                                        or abs(img_height - canvas_height) > 10
                                    ):
                                        # Calculate aspect-preserving size
                                        img_ratio = img_width / img_height
                                        canvas_ratio = canvas_width / canvas_height

                                        if img_ratio > canvas_ratio:
                                            new_width = canvas_width
                                            new_height = int(canvas_width / img_ratio)
                                        else:
                                            new_height = canvas_height
                                            new_width = int(canvas_height * img_ratio)

                                        # Use NEAREST for speed
                                        pil_image = pil_image.resize(
                                            (new_width, new_height), Image.NEAREST
                                        )

                                # Convert to PhotoImage for Tkinter and blit to screen
                                with vj_profiler.profile("vj_blit_to_screen"):
                                    photo = ImageTk.PhotoImage(pil_image)

                                    # Update canvas
                                    self.canvas.delete("all")
                                    x = canvas_width // 2
                                    y = canvas_height // 2
                                    self.canvas.create_image(
                                        x, y, image=photo, anchor=tk.CENTER
                                    )

                                    # Keep a reference to prevent garbage collection
                                    self.canvas.image = photo

                            except Exception as e:
                                print(f"Error processing VJ image: {e}")

            # Schedule next frame (60 FPS target - we can handle it now)
            self.after(16, self._animate)

        except Exception as e:
            print(f"❌ VJ Animation error: {e}")
            import traceback

            traceback.print_exc()
            self.stop_animation()

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

    def _on_key_press(self, event):
        """Handle keyboard events"""
        if event.keysym == "space":
            self.shift_scene()
        elif event.keysym == "Escape":
            self._on_closing()

    def shift_scene(self):
        """Shift scene using current system mode"""
        if self.vj_frame:
            self.vj_frame.shift_scene()

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
