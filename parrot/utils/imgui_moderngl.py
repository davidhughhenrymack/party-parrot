"""ImGui renderer for ModernGL with Pyglet input handling"""

import imgui
import moderngl as mgl
import numpy as np
import ctypes
from beartype import beartype


@beartype
class ImGuiModernGLRenderer:
    """Custom ImGui renderer for ModernGL that integrates with Pyglet for input"""

    def __init__(
        self,
        ctx: mgl.Context,
        pyglet_window,
        fixed_width: int = 1920,
        fixed_height: int = 1080,
    ):
        self.ctx = ctx
        self.pyglet_window = pyglet_window
        self.fixed_width = fixed_width
        self.fixed_height = fixed_height

        # Setup ImGui IO
        self.io = imgui.get_io()
        # Set fixed display size for ImGui
        self.io.display_size = fixed_width, fixed_height

        # Create fixed-size framebuffer for ImGui rendering
        self._create_imgui_framebuffer()

        # Create font texture
        self._create_font_texture()

        # Create shader program for ImGui
        self._create_shader()

        # Create blit shader for copying ImGui framebuffer to screen
        self._create_blit_shader()

        # Setup input callbacks
        if pyglet_window:
            self._setup_input_callbacks()

    def _create_imgui_framebuffer(self):
        """Create fixed-size framebuffer for ImGui rendering"""
        self.imgui_texture = self.ctx.texture((self.fixed_width, self.fixed_height), 4)
        self.imgui_texture.filter = (mgl.LINEAR, mgl.LINEAR)
        self.imgui_fbo = self.ctx.framebuffer(color_attachments=[self.imgui_texture])

    def _create_font_texture(self):
        """Create font texture"""
        width, height, pixels = self.io.fonts.get_tex_data_as_rgba32()

        self.font_texture = self.ctx.texture((width, height), 4, data=pixels)
        self.font_texture.filter = (mgl.LINEAR, mgl.LINEAR)

        self.io.fonts.texture_id = self.font_texture.glo
        self.io.fonts.clear_tex_data()

    def _create_shader(self):
        """Create shader program for ImGui rendering"""
        vertex_shader = """
        #version 330
        uniform mat4 ProjMtx;
        in vec2 Position;
        in vec2 UV;
        in vec4 Color;
        out vec2 Frag_UV;
        out vec4 Frag_Color;
        void main() {
            Frag_UV = UV;
            Frag_Color = Color;
            gl_Position = ProjMtx * vec4(Position.xy, 0, 1);
        }
        """

        fragment_shader = """
        #version 330
        uniform sampler2D Texture;
        in vec2 Frag_UV;
        in vec4 Frag_Color;
        out vec4 Out_Color;
        void main() {
            Out_Color = Frag_Color * texture(Texture, Frag_UV.st);
        }
        """

        self.shader = self.ctx.program(
            vertex_shader=vertex_shader, fragment_shader=fragment_shader
        )

    def _create_blit_shader(self):
        """Create shader for blitting ImGui framebuffer to screen"""
        blit_vertex = """
        #version 330
        in vec2 in_position;
        in vec2 in_uv;
        out vec2 v_uv;
        void main() {
            v_uv = in_uv;
            gl_Position = vec4(in_position, 0.0, 1.0);
        }
        """

        blit_fragment = """
        #version 330
        uniform sampler2D imgui_tex;
        uniform vec2 imgui_size;
        uniform vec2 window_size;
        in vec2 v_uv;
        out vec4 fragColor;
        void main() {
            // OpenGL screen: (0,0) = bottom-left
            // ImGui wants: (0,0) = top-left
            // v_uv.x = 0 -> left, v_uv.x = 1 -> right
            // v_uv.y = 0 -> bottom, v_uv.y = 1 -> top
            
            // For top-left aligned ImGui region:
            // Top-left of screen = v_uv(0, 0) should map to ImGui(0, 0)
            // Bottom-left of screen = v_uv(0, 1) should be outside if below ImGui region
            
            float pixel_x = v_uv.x * window_size.x;
            float pixel_y_from_bottom = v_uv.y * window_size.y;
            
            // Convert to distance from top
            float pixel_y_from_top = window_size.y - pixel_y_from_bottom;
            
            // Check if within ImGui region (top-left aligned)
            if (pixel_x >= imgui_size.x || pixel_y_from_top >= imgui_size.y || pixel_y_from_top < 0.0) {
                fragColor = vec4(0.0, 0.0, 0.0, 0.0);
            } else {
                // Map to ImGui texture coordinates
                vec2 imgui_uv = vec2(pixel_x / imgui_size.x, pixel_y_from_top / imgui_size.y);
                fragColor = texture(imgui_tex, imgui_uv);
            }
        }
        """

        self.blit_shader = self.ctx.program(
            vertex_shader=blit_vertex, fragment_shader=blit_fragment
        )

        # Create full-screen quad for blitting
        # Positions in NDC, UVs for texture sampling
        vertices = np.array(
            [
                # pos_x, pos_y, uv_x, uv_y
                -1.0,
                -1.0,
                0.0,
                0.0,
                1.0,
                -1.0,
                1.0,
                0.0,
                -1.0,
                1.0,
                0.0,
                1.0,
                1.0,
                1.0,
                1.0,
                1.0,
            ],
            dtype=np.float32,
        )

        self.blit_vbo = self.ctx.buffer(vertices.tobytes())
        self.blit_vao = self.ctx.vertex_array(
            self.blit_shader, [(self.blit_vbo, "2f 2f", "in_position", "in_uv")]
        )

    def _setup_input_callbacks(self):
        """Setup pyglet input callbacks"""

        def scale_mouse_coords(x, y):
            """Scale window coordinates to fixed ImGui coordinate space"""
            # Scale from window coordinates to ImGui's fixed coordinate space
            imgui_x = (x / self.pyglet_window.width) * self.fixed_width
            imgui_y = (
                (self.pyglet_window.height - y) / self.pyglet_window.height
            ) * self.fixed_height
            return imgui_x, imgui_y

        @self.pyglet_window.event
        def on_mouse_motion(x, y, dx, dy):
            self.io.mouse_pos = scale_mouse_coords(x, y)

        @self.pyglet_window.event
        def on_mouse_drag(x, y, dx, dy, buttons, modifiers):
            self.io.mouse_pos = scale_mouse_coords(x, y)

        @self.pyglet_window.event
        def on_mouse_press(x, y, button, modifiers):
            self.io.mouse_pos = scale_mouse_coords(x, y)
            if button == 1:  # Left button
                self.io.mouse_down[0] = True
            elif button == 4:  # Right button
                self.io.mouse_down[1] = True

        @self.pyglet_window.event
        def on_mouse_release(x, y, button, modifiers):
            if button == 1:  # Left button
                self.io.mouse_down[0] = False
            elif button == 4:  # Right button
                self.io.mouse_down[1] = False

        # Note: We don't update display_size on resize - it stays fixed
        # Mouse coordinates are scaled to the fixed ImGui coordinate space

    def render(self, draw_data):
        """Render ImGui draw data to fixed-size framebuffer, then blit to screen"""
        io = self.io
        display_width, display_height = io.display_size
        fb_width = int(display_width * io.display_fb_scale[0])
        fb_height = int(display_height * io.display_fb_scale[1])

        if fb_width == 0 or fb_height == 0:
            return

        # Backup GL state
        last_viewport = self.ctx.viewport
        last_scissor = self.ctx.scissor
        last_fbo = self.ctx.fbo

        # Bind ImGui framebuffer and clear it
        self.imgui_fbo.use()
        self.imgui_fbo.clear(0.0, 0.0, 0.0, 0.0)
        self.ctx.viewport = (0, 0, self.fixed_width, self.fixed_height)

        # ModernGL doesn't let us read state flags, so we'll use a scope
        # to ensure state is properly managed
        # Save what we can and make sure to restore properly

        # Setup render state for ImGui
        self.ctx.enable(mgl.BLEND)
        self.ctx.blend_func = mgl.SRC_ALPHA, mgl.ONE_MINUS_SRC_ALPHA
        self.ctx.disable(mgl.CULL_FACE)
        self.ctx.disable(mgl.DEPTH_TEST)

        # Setup orthographic projection matrix
        L, R = 0.0, io.display_size[0]
        T, B = 0.0, io.display_size[1]
        ortho_projection = np.array(
            [
                [2.0 / (R - L), 0.0, 0.0, 0.0],
                [0.0, 2.0 / (T - B), 0.0, 0.0],
                [0.0, 0.0, -1.0, 0.0],
                [(R + L) / (L - R), (T + B) / (B - T), 0.0, 1.0],
            ],
            dtype=np.float32,
        )

        self.shader["ProjMtx"].write(ortho_projection.tobytes())
        self.shader["Texture"] = 0

        # Render command lists
        for commands in draw_data.commands_lists:
            # Get vertex and index data
            idx_buffer_offset = 0

            # Get buffer data - the data is a pointer (int), convert to bytes
            vtx_size = commands.vtx_buffer_size * imgui.VERTEX_SIZE
            idx_size = commands.idx_buffer_size * imgui.INDEX_SIZE

            # Convert pointer to bytes using ctypes
            vtx_ptr = ctypes.cast(
                commands.vtx_buffer_data, ctypes.POINTER(ctypes.c_byte)
            )
            idx_ptr = ctypes.cast(
                commands.idx_buffer_data, ctypes.POINTER(ctypes.c_byte)
            )

            vtx_buffer = ctypes.string_at(vtx_ptr, vtx_size)
            idx_buffer = ctypes.string_at(idx_ptr, idx_size)

            # Create VBO and IBO
            vbo = self.ctx.buffer(data=vtx_buffer)
            ibo = self.ctx.buffer(data=idx_buffer)

            # Create VAO
            vao = self.ctx.vertex_array(
                self.shader, [(vbo, "2f 2f 4f1", "Position", "UV", "Color")], ibo
            )

            for command in commands.commands:
                # Set scissor
                x, y, z, w = command.clip_rect
                self.ctx.scissor = int(x), int(fb_height - w), int(z - x), int(w - y)

                # Bind texture - always use font texture for now
                # (ImGui's texture_id is the OpenGL texture ID)
                self.font_texture.use(0)

                # Draw
                vao.render(
                    mgl.TRIANGLES, vertices=command.elem_count, first=idx_buffer_offset
                )
                idx_buffer_offset += command.elem_count

            # Cleanup
            vao.release()
            vbo.release()
            ibo.release()

        # Restore framebuffer to main screen
        last_fbo.use()
        self.ctx.viewport = last_viewport
        if last_scissor is None:
            self.ctx.scissor = None
        else:
            self.ctx.scissor = last_scissor

        # Blit ImGui framebuffer to screen with aspect ratio correction
        self.ctx.enable(mgl.BLEND)
        self.ctx.blend_func = mgl.SRC_ALPHA, mgl.ONE_MINUS_SRC_ALPHA
        self.imgui_texture.use(0)
        self.blit_shader["imgui_tex"] = 0
        self.blit_shader["imgui_size"].value = (
            float(self.fixed_width),
            float(self.fixed_height),
        )
        self.blit_shader["window_size"].value = (
            float(last_viewport[2]),
            float(last_viewport[3]),
        )
        self.blit_vao.render(mgl.TRIANGLE_STRIP)

        # CRITICAL: LayerCompose expects BLEND to be disabled
        # It enables/disables blend for each layer composition
        # We must leave it disabled after ImGui rendering
        self.ctx.disable(mgl.BLEND)

    def shutdown(self):
        """Cleanup resources"""
        if hasattr(self, "font_texture"):
            self.font_texture.release()
        if hasattr(self, "shader"):
            self.shader.release()
        if hasattr(self, "imgui_texture"):
            self.imgui_texture.release()
        if hasattr(self, "imgui_fbo"):
            self.imgui_fbo.release()
        if hasattr(self, "blit_shader"):
            self.blit_shader.release()
        if hasattr(self, "blit_vbo"):
            self.blit_vbo.release()
        if hasattr(self, "blit_vao"):
            self.blit_vao.release()
