#!/usr/bin/env python3

import moderngl as mgl
import moderngl_window as mglw
from moderngl_window import geometry
import numpy as np
from beartype import beartype
from typing import Optional

from parrot.director.frame import Frame
from parrot.director.color_scheme import ColorScheme
from parrot.vj.nodes.video_player import VideoPlayer


@beartype
class VJWindow(mglw.WindowConfig):
    """
    ModernGL window for VJ system that displays video content fullscreen
    """

    gl_version = (3, 3)
    title = "Party Parrot VJ"
    window_size = (1920, 1080)
    fullscreen = False  # Can be set to True for fullscreen mode
    resizable = True

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

        # VJ system components
        self.video_player: Optional[VideoPlayer] = None
        self.blit_program: Optional[mgl.Program] = None
        self.quad_vao: Optional[mgl.VertexArray] = None

        # Frame data
        self.current_frame: Optional[Frame] = None
        self.current_scheme: Optional[ColorScheme] = None

        self._setup_blit_resources()

    def _setup_blit_resources(self):
        """Setup resources for blitting framebuffers to screen"""
        # Vertex shader for fullscreen quad
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

        # Fragment shader for blitting
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

        # Create fullscreen quad
        vertices = np.array(
            [
                # Position  # TexCoord
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

    def set_video_player(self, video_player: VideoPlayer):
        """Set the video player node"""
        self.video_player = video_player
        if self.video_player:
            self.video_player.enter(self.ctx)
            # Generate initial video selection
            from parrot.graph.BaseInterpretationNode import Vibe
            from parrot.director.mode import Mode

            self.video_player.generate(Vibe(Mode.gentle))

    def step(self, frame: Frame, scheme: ColorScheme):
        """Update the VJ system with new frame data"""
        self.current_frame = frame
        self.current_scheme = scheme

    def render(self, time: float, frame_time: float):
        """Render the VJ content to the screen"""
        # Clear the screen
        self.ctx.clear(0.0, 0.0, 0.0)

        if not self.video_player or not self.current_frame or not self.current_scheme:
            return

        # Render the video player
        try:
            fbo = self.video_player.render(
                self.current_frame, self.current_scheme, self.ctx
            )

            if fbo and fbo.color_attachments:
                # Blit the framebuffer to screen
                self.blit_to_screen(fbo)
        except Exception as e:
            print(f"Error rendering video: {e}")

    def blit_to_screen(self, fbo: mgl.Framebuffer):
        """Blit a framebuffer to the screen"""
        if not fbo.color_attachments:
            return

        # Use the default framebuffer (screen)
        self.ctx.screen.use()

        # Bind the source texture
        texture = fbo.color_attachments[0]
        texture.use(0)
        self.blit_program["source_texture"] = 0

        # Render fullscreen quad
        self.quad_vao.render(mgl.TRIANGLE_STRIP)

    def resize(self, width: int, height: int):
        """Handle window resize"""
        self.ctx.viewport = (0, 0, width, height)

    def key_event(self, key, action, modifiers):
        """Handle keyboard events"""
        if action == self.wnd.keys.ACTION_PRESS:
            if key == self.wnd.keys.ESCAPE:
                self.wnd.close()
            elif key == self.wnd.keys.F11:
                # Toggle fullscreen
                self.wnd.fullscreen = not self.wnd.fullscreen
            elif key == self.wnd.keys.SPACE:
                # Regenerate video player (pick new video group)
                if self.video_player:
                    from parrot.graph.BaseInterpretationNode import Vibe
                    from parrot.director.mode import Mode

                    self.video_player.generate(Vibe(Mode.gentle))

    def close(self):
        """Clean up resources when closing"""
        if self.video_player:
            self.video_player.exit()


@beartype
class VJWindowManager:
    """
    Manager class for the VJ window that can be integrated with the main application
    """

    def __init__(self, vj_director=None):
        self.window: Optional[VJWindow] = None
        self.video_player: Optional[VideoPlayer] = None
        self.vj_director = vj_director

    def create_window(self, fullscreen: bool = False):
        """Create and setup the VJ window"""
        # Configure window settings
        VJWindow.fullscreen = fullscreen

        # Create video player
        self.video_player = VideoPlayer(fn_group="bg")

        # The window will be created by moderngl_window when run() is called
        # We'll set up the video player in the window's __init__ method

    def get_window_class(self) -> type:
        """Get the window class configured with our video player"""
        video_player = self.video_player
        vj_director = self.vj_director

        class ConfiguredVJWindow(VJWindow):
            def __init__(self, **kwargs):
                super().__init__(**kwargs)
                if video_player:
                    self.set_video_player(video_player)
                if vj_director:
                    self.vj_director = vj_director

            def render(self, time: float, frame_time: float):
                """Override render to use VJ director if available"""
                self.ctx.clear(0.0, 0.0, 0.0)

                if (
                    self.vj_director
                    and hasattr(self.vj_director, "canvas")
                    and self.vj_director.canvas
                ):
                    # Use VJ director's canvas
                    if hasattr(self, "current_frame") and hasattr(
                        self, "current_scheme"
                    ):
                        try:
                            fbo = self.vj_director.render(
                                self.ctx, self.current_frame, self.current_scheme
                            )
                            if fbo:
                                self.blit_to_screen(fbo)
                        except Exception as e:
                            print(f"Error rendering VJ director: {e}")
                else:
                    # Fall back to original render method
                    super().render(time, frame_time)

        return ConfiguredVJWindow

    def step(self, frame: Frame, scheme: ColorScheme):
        """Update the VJ system - this will be called from the main director"""
        # This method will be used when integrating with the main system
        # For now, the window handles its own rendering loop
        pass
