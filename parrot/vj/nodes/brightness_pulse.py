#!/usr/bin/env python3

import numpy as np
import moderngl as mgl
from typing import Optional
from beartype import beartype

from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme


@beartype
class BrightnessPulse(
    BaseInterpretationNode[mgl.Context, mgl.Framebuffer, mgl.Framebuffer]
):
    """
    A brightness modulation node that pulses the brightness of its input based on low frequencies.
    Takes a video input (framebuffer) and modulates its brightness using frame.freq_low.
    """

    def __init__(
        self,
        input_node: BaseInterpretationNode[mgl.Context, None, mgl.Framebuffer],
        intensity: float = 1.0,
        base_brightness: float = 0.3,
    ):
        """
        Args:
            input_node: The node that provides the video input (e.g., VideoPlayer)
            intensity: How strong the pulse effect is (0.0 = no effect, 1.0 = full range)
            base_brightness: Minimum brightness level (0.0 = black, 1.0 = full brightness)
        """
        super().__init__([input_node])
        self.input_node = input_node
        self.intensity = intensity
        self.base_brightness = base_brightness

        # OpenGL resources
        self.framebuffer: Optional[mgl.Framebuffer] = None
        self.texture: Optional[mgl.Texture] = None
        self.shader_program: Optional[mgl.Program] = None
        self.quad_vao: Optional[mgl.VertexArray] = None

    def enter(self, context: mgl.Context):
        """Initialize brightness modulation resources"""
        self._setup_gl_resources(context)

    def exit(self):
        """Clean up brightness modulation resources"""
        if self.framebuffer:
            self.framebuffer.release()
            self.framebuffer = None
        if self.texture:
            self.texture.release()
            self.texture = None
        if self.shader_program:
            self.shader_program.release()
            self.shader_program = None
        if self.quad_vao:
            self.quad_vao.release()
            self.quad_vao = None

    def generate(self, vibe: Vibe):
        """Configure brightness pulse parameters based on the vibe"""
        # Could randomize intensity and base_brightness based on vibe.mode
        # For now, keep the initialized values
        pass

    def _setup_gl_resources(
        self, context: mgl.Context, width: int = 1920, height: int = 1080
    ):
        """Setup OpenGL resources for brightness modulation"""
        if not self.texture:
            self.texture = context.texture((width, height), 3)  # RGB texture
            self.framebuffer = context.framebuffer(color_attachments=[self.texture])

        if not self.shader_program:
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

            # Fragment shader for brightness modulation
            fragment_shader = """
            #version 330 core
            in vec2 uv;
            out vec3 color;
            uniform sampler2D input_texture;
            uniform float brightness_multiplier;
            
            void main() {
                vec3 input_color = texture(input_texture, uv).rgb;
                color = input_color * brightness_multiplier;
            }
            """

            self.shader_program = context.program(
                vertex_shader=vertex_shader, fragment_shader=fragment_shader
            )

        if not self.quad_vao:
            # Create fullscreen quad
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

            vbo = context.buffer(vertices.tobytes())
            self.quad_vao = context.vertex_array(
                self.shader_program, [(vbo, "2f 2f", "in_position", "in_texcoord")]
            )

    def render(
        self, frame: Frame, scheme: ColorScheme, context: mgl.Context
    ) -> mgl.Framebuffer:
        """
        Render the input with brightness modulated by low frequencies.
        """
        # Get the input framebuffer from the child node
        input_framebuffer = self.input_node.render(frame, scheme, context)

        if not input_framebuffer or not input_framebuffer.color_attachments:
            # Return a black framebuffer if no input
            if not self.framebuffer:
                self._setup_gl_resources(context)
            self.framebuffer.use()
            context.clear(0.0, 0.0, 0.0)
            return self.framebuffer

        # Calculate brightness multiplier based on low frequencies
        low_freq = frame[FrameSignal.freq_low]  # This should be 0.0 to 1.0

        # Map low frequency to brightness: base_brightness + (intensity * low_freq)
        # This ensures brightness ranges from base_brightness to (base_brightness + intensity)
        brightness_multiplier = self.base_brightness + (self.intensity * low_freq)

        # Clamp to reasonable range
        brightness_multiplier = max(0.0, min(2.0, brightness_multiplier))

        # Setup framebuffer and render
        if not self.framebuffer:
            self._setup_gl_resources(context)

        self.framebuffer.use()
        context.clear(0.0, 0.0, 0.0)

        # Bind input texture
        input_framebuffer.color_attachments[0].use(0)

        # Set uniforms and render
        self.shader_program["input_texture"] = 0
        self.shader_program["brightness_multiplier"] = brightness_multiplier

        self.quad_vao.render(mgl.TRIANGLE_STRIP)

        return self.framebuffer
