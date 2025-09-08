"""
ModernGL-based VJ renderer for high-performance layer compositing
"""

import os
from typing import Optional, List, Tuple
import numpy as np
from parrot.director.frame import Frame
from parrot.director.color_scheme import ColorScheme
from parrot.vj.base import LayerBase
from parrot.vj.config import CONFIG

import moderngl

try:
    from PIL import Image

    HAS_PIL = True
except ImportError:
    HAS_PIL = False


class ModernGLRenderer:
    """High-performance VJ renderer using ModernGL for GPU-accelerated compositing"""

    def __init__(self, width: int = 1920, height: int = 1080, headless: bool = True):
        self.width = width
        self.height = height
        self.layers: List[LayerBase] = []

        # OpenGL context and resources
        self.ctx: Optional["moderngl.Context"] = None
        self.fbo: Optional["moderngl.Framebuffer"] = None
        self.quad_vao = None
        self.blend_program = None
        self.copy_program = None

        # Textures
        self.output_texture = None
        self.temp_texture = None

        # Initialize OpenGL
        self._init_opengl(headless)

        self._initialized = self.ctx is not None

    def _init_opengl(self, headless: bool):
        """Initialize ModernGL context and resources"""
        try:
            # Create context
            if headless:
                # Create headless context (no window required)
                self.ctx = moderngl.create_context(standalone=True)
            else:
                # For GUI integration, we might need a different approach
                self.ctx = moderngl.create_context()

            # Enable alpha blending
            self.ctx.enable(moderngl.BLEND)
            self.ctx.blend_func = moderngl.SRC_ALPHA, moderngl.ONE_MINUS_SRC_ALPHA

            # Create output texture
            self.output_texture = self.ctx.texture((self.width, self.height), 4)
            self.temp_texture = self.ctx.texture((self.width, self.height), 4)

            # Create framebuffer
            self.fbo = self.ctx.framebuffer(self.output_texture)

            # Create shader programs
            self._create_shaders()

            # Create quad VAO for fullscreen rendering
            self._create_quad()

            print(f"ModernGL VJ Renderer initialized ({self.width}x{self.height})")

        except Exception as e:
            print(f"Failed to initialize ModernGL: {e}")
            self.ctx = None

    def _create_shaders(self):
        """Create shader programs for layer compositing"""
        # Vertex shader for fullscreen quad
        vertex_shader = """
        #version 330 core
        in vec2 in_position;
        in vec2 in_texcoord;
        out vec2 v_texcoord;
        
        void main() {
            gl_Position = vec4(in_position, 0.0, 1.0);
            v_texcoord = in_texcoord;
        }
        """

        # Fragment shader for alpha blending
        blend_fragment = """
        #version 330 core
        uniform sampler2D background;
        uniform sampler2D foreground;
        uniform float alpha;
        in vec2 v_texcoord;
        out vec4 fragColor;
        
        void main() {
            vec4 bg = texture(background, v_texcoord);
            vec4 fg = texture(foreground, v_texcoord);
            
            // Apply layer alpha
            fg.a *= alpha;
            
            // Alpha blending
            float out_alpha = fg.a + bg.a * (1.0 - fg.a);
            vec3 out_color = (fg.rgb * fg.a + bg.rgb * bg.a * (1.0 - fg.a)) / max(out_alpha, 0.001);
            
            fragColor = vec4(out_color, out_alpha);
        }
        """

        # Fragment shader for simple copy
        copy_fragment = """
        #version 330 core
        uniform sampler2D texture0;
        in vec2 v_texcoord;
        out vec4 fragColor;
        
        void main() {
            fragColor = texture(texture0, v_texcoord);
        }
        """

        self.blend_program = self.ctx.program(
            vertex_shader=vertex_shader, fragment_shader=blend_fragment
        )

        self.copy_program = self.ctx.program(
            vertex_shader=vertex_shader, fragment_shader=copy_fragment
        )

    def _create_quad(self):
        """Create a fullscreen quad for rendering"""
        # Quad vertices (position, texcoord)
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
                1.0,
                1.0,
                1.0,
                1.0,  # Top-right
                -1.0,
                1.0,
                0.0,
                1.0,  # Top-left
            ],
            dtype=np.float32,
        )

        indices = np.array([0, 1, 2, 2, 3, 0], dtype=np.uint32)

        vbo = self.ctx.buffer(vertices.tobytes())
        ibo = self.ctx.buffer(indices.tobytes())

        self.quad_vao = self.ctx.vertex_array(
            self.blend_program, [(vbo, "2f 2f", "in_position", "in_texcoord")], ibo
        )

    def add_layer(self, layer: LayerBase):
        """Add a layer to the renderer"""
        self.layers.append(layer)
        # Sort layers by z_order (lower values render first, higher on top)
        self.layers.sort(key=lambda l: l.z_order)

    def remove_layer(self, layer: LayerBase):
        """Remove a layer from the renderer"""
        if layer in self.layers:
            self.layers.remove(layer)

    def clear_layers(self):
        """Remove all layers"""
        self.layers.clear()

    def render_frame(self, frame: Frame, scheme: ColorScheme) -> Optional[np.ndarray]:
        """Render all layers and composite them into a single frame"""
        # Set size on all layers to match renderer
        for layer in self.layers:
            layer.set_size(self.width, self.height)

        if not self._initialized or not self.layers:
            # Fallback to CPU rendering
            return self._render_frame_cpu(frame, scheme)

        try:
            # Clear the framebuffer
            self.fbo.use()
            self.ctx.clear(0.0, 0.0, 0.0, 0.0)  # Transparent black

            background_texture = None

            # Render each layer in z_order
            for layer in self.layers:
                if not layer.is_enabled():
                    continue

                layer_data = layer.render(frame, scheme)
                if layer_data is None:
                    continue

                # Upload layer data to GPU
                layer_texture = self._upload_texture(layer_data)
                if layer_texture is None:
                    continue

                # Composite this layer
                if background_texture is None:
                    # First layer - just copy
                    self._copy_texture(layer_texture, layer.get_alpha())
                    background_texture = self.output_texture
                else:
                    # Blend with previous layers
                    self._blend_textures(
                        background_texture, layer_texture, layer.get_alpha()
                    )

                # Clean up temporary texture
                layer_texture.release()

            # Read back the result
            result = self._read_framebuffer()
            return result

        except Exception as e:
            print(f"Error in ModernGL rendering: {e}")
            # Fallback to CPU rendering
            return self._render_frame_cpu(frame, scheme)

    def _upload_texture(self, data: np.ndarray) -> Optional["moderngl.Texture"]:
        """Upload numpy array to GPU texture"""
        try:
            # Ensure data is the right format
            if data.shape[:2] != (self.height, self.width):
                # Resize if needed
                if HAS_PIL:
                    pil_img = Image.fromarray(data)
                    pil_img = pil_img.resize((self.width, self.height), Image.LANCZOS)
                    data = np.array(pil_img)
                else:
                    # Skip if can't resize
                    return None

            # Ensure RGBA format
            if data.shape[2] == 3:
                # Add alpha channel
                alpha = np.full(
                    (data.shape[0], data.shape[1], 1), 255, dtype=data.dtype
                )
                data = np.concatenate([data, alpha], axis=2)

            # Create texture and upload data
            texture = self.ctx.texture((self.width, self.height), 4)
            texture.write(data.tobytes())
            return texture

        except Exception as e:
            print(f"Error uploading texture: {e}")
            return None

    def _copy_texture(self, texture: "moderngl.Texture", alpha: float):
        """Copy texture to output with alpha"""
        self.copy_program["texture0"] = 0
        texture.use(0)

        # For first layer, we can just copy directly
        self.quad_vao.render()

    def _blend_textures(
        self,
        background: "moderngl.Texture",
        foreground: "moderngl.Texture",
        alpha: float,
    ):
        """Blend foreground texture onto background"""
        self.blend_program["background"] = 0
        self.blend_program["foreground"] = 1
        self.blend_program["alpha"] = alpha

        background.use(0)
        foreground.use(1)

        self.quad_vao.render()

    def _read_framebuffer(self) -> np.ndarray:
        """Read the framebuffer back to CPU memory"""
        # Read RGBA data
        data = self.fbo.read(components=4)

        # Convert to numpy array and reshape
        result = np.frombuffer(data, dtype=np.uint8)
        result = result.reshape((self.height, self.width, 4))

        # OpenGL has origin at bottom-left, flip vertically
        result = np.flipud(result)

        return result

    def _render_frame_cpu(
        self, frame: Frame, scheme: ColorScheme
    ) -> Optional[np.ndarray]:
        """CPU fallback rendering when ModernGL is not available"""
        if not self.layers:
            return None

        # Set size on all layers to match renderer
        for layer in self.layers:
            layer.set_size(self.width, self.height)

        # Start with a transparent black background
        final_frame = np.zeros((self.height, self.width, 4), dtype=np.uint8)

        # Render each layer in z_order
        for layer in self.layers:
            if not layer.is_enabled():
                continue

            try:
                layer_data = layer.render(frame, scheme)
                if layer_data is None:
                    continue
            except Exception as e:
                print(f"Error rendering layer {layer}: {e}")
                continue

            # Ensure layer data is the right size
            if layer_data.shape[:2] != (self.height, self.width):
                # For now, skip layers that don't match our resolution
                continue

            # Apply layer alpha
            if layer.get_alpha() < 1.0:
                layer_data = layer_data.copy()
                layer_data[:, :, 3] = (layer_data[:, :, 3] * layer.get_alpha()).astype(
                    np.uint8
                )

            # Alpha blend this layer onto the final frame
            final_frame = self._alpha_blend_cpu(final_frame, layer_data)

        return final_frame

    def _alpha_blend_cpu(
        self, background: np.ndarray, foreground: np.ndarray
    ) -> np.ndarray:
        """CPU alpha blending"""
        # Convert to float for calculations
        bg = background.astype(np.float32) / 255.0
        fg = foreground.astype(np.float32) / 255.0

        # Extract alpha channels
        bg_alpha = bg[:, :, 3:4]
        fg_alpha = fg[:, :, 3:4]

        # Calculate output alpha
        out_alpha = fg_alpha + bg_alpha * (1.0 - fg_alpha)

        # Avoid division by zero
        out_alpha_safe = np.where(out_alpha == 0, 1, out_alpha)

        # Calculate output RGB
        out_rgb = (
            fg[:, :, :3] * fg_alpha + bg[:, :, :3] * bg_alpha * (1.0 - fg_alpha)
        ) / out_alpha_safe

        # Combine RGB and alpha
        result = np.concatenate([out_rgb, out_alpha], axis=2)

        # Convert back to uint8
        return (result * 255).astype(np.uint8)

    def resize(self, width: int, height: int):
        """Resize the renderer and recreate OpenGL resources"""
        if self.width == width and self.height == height:
            return

        self.width = width
        self.height = height

        # Resize layers
        for layer in self.layers:
            layer.resize(width, height)

        # Recreate OpenGL resources if initialized
        if self._initialized:
            try:
                # Release old resources
                if self.output_texture:
                    self.output_texture.release()
                if self.temp_texture:
                    self.temp_texture.release()
                if self.fbo:
                    self.fbo.release()

                # Create new textures and framebuffer
                self.output_texture = self.ctx.texture((self.width, self.height), 4)
                self.temp_texture = self.ctx.texture((self.width, self.height), 4)
                self.fbo = self.ctx.framebuffer(self.output_texture)

                print(f"ModernGL VJ Renderer resized to {width}x{height}")

            except Exception as e:
                print(f"Error resizing ModernGL renderer: {e}")
                self._initialized = False

    def get_size(self) -> Tuple[int, int]:
        """Get the renderer size"""
        return (self.width, self.height)

    def cleanup(self):
        """Clean up OpenGL resources"""
        if self._initialized:
            try:
                if self.output_texture:
                    self.output_texture.release()
                if self.temp_texture:
                    self.temp_texture.release()
                if self.fbo:
                    self.fbo.release()
                if self.quad_vao:
                    self.quad_vao.release()
                if self.blend_program:
                    self.blend_program.release()
                if self.copy_program:
                    self.copy_program.release()

                print("ModernGL VJ Renderer cleaned up")
            except Exception as e:
                print(f"Error cleaning up ModernGL renderer: {e}")

        self._initialized = False

    def __del__(self):
        """Cleanup when renderer is destroyed"""
        self.cleanup()


# Alias for backward compatibility
VJRenderer = ModernGLRenderer
