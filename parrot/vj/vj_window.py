#!/usr/bin/env python3

import moderngl as mgl
import moderngl_window as mglw
import numpy as np
from beartype import beartype

from parrot.director.frame import Frame
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode


@beartype
class VJWindow(mglw.WindowConfig):
    """VJ window for displaying rendered content"""

    gl_version = (3, 3)
    title = "Party Parrot VJ"
    window_size = (1920, 1080)
    fullscreen = False
    resizable = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.blit_program = None
        self.quad_vao = None
        self.vj_director = None
        self._setup_blit_resources()

    def _setup_blit_resources(self):
        """Setup resources for blitting framebuffers to screen"""
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

        self.blit_program = self.ctx.program(
            vertex_shader=vertex_shader, fragment_shader=fragment_shader
        )

        vertices = np.array(
            [
                -1.0,
                -1.0,
                0.0,
                1.0,  # Bottom-left
                1.0,
                -1.0,
                1.0,
                1.0,  # Bottom-right
                -1.0,
                1.0,
                0.0,
                0.0,  # Top-left
                1.0,
                1.0,
                1.0,
                0.0,  # Top-right
            ],
            dtype=np.float32,
        )

        vbo = self.ctx.buffer(vertices.tobytes())
        self.quad_vao = self.ctx.vertex_array(
            self.blit_program, [(vbo, "2f 2f", "in_position", "in_texcoord")]
        )

    def render_vj_frame(self, frame: Frame, scheme: ColorScheme):
        """Render VJ frame (called from VJ director)"""
        if self.vj_director:
            fbo = self.vj_director.render(self.ctx, frame, scheme)
            if fbo and fbo.color_attachments:
                self.blit_to_screen(fbo)

    def blit_to_screen(self, fbo: mgl.Framebuffer):
        """Blit a framebuffer to the screen"""
        self.ctx.screen.use()
        texture = fbo.color_attachments[0]
        texture.use(0)
        self.blit_program["source_texture"] = 0
        self.quad_vao.render(mgl.TRIANGLE_STRIP)

    def shift_scene(self):
        """Shift scene using current system mode"""
        if self.vj_director:
            current_mode = self.vj_director.get_current_mode()
            print(f"VJ Scene shift with current mode: {current_mode}")
            self.vj_director.shift_current_mode()
        else:
            print("VJ Director not available for scene shift")

    def render(self, time: float, frame_time: float):
        """Render method - gets latest frame and renders VJ content"""
        self.ctx.clear(0.0, 0.0, 0.0)

        # Get latest frame data from VJ director if available
        if self.vj_director:
            frame, scheme = self.vj_director.get_latest_frame_data()
            if frame is not None and scheme is not None:
                self.render_vj_frame(frame, scheme)

    def key_event(self, key, action, modifiers):
        """Handle keyboard events"""
        if action == self.wnd.keys.ACTION_PRESS:
            if key == self.wnd.keys.ESCAPE:
                self.wnd.close()
            elif key == self.wnd.keys.F11:
                self.wnd.fullscreen = not self.wnd.fullscreen
            elif key == self.wnd.keys.SPACE:
                self.shift_scene()


@beartype
class VJWindowManager:
    """Manager for VJ window integration"""

    def __init__(self, vj_director):
        self.vj_director = vj_director

    def create_window(self, fullscreen: bool = False):
        """Configure window settings"""
        VJWindow.fullscreen = fullscreen

    def get_window_class(self) -> type:
        """Get configured window class with VJ director"""
        vj_director = self.vj_director

        class ConfiguredVJWindow(VJWindow):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                self.vj_director = vj_director
                vj_director.setup(self.ctx)
                vj_director.set_window(self)

        return ConfiguredVJWindow
