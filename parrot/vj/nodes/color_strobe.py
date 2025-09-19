#!/usr/bin/env python3

import time
import random
import moderngl as mgl
from beartype.typing import Tuple
from beartype import beartype

from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode
from parrot.vj.constants import DEFAULT_WIDTH, DEFAULT_HEIGHT


@beartype
class ColorStrobe(BaseInterpretationNode[mgl.Context, None, mgl.Framebuffer]):
    """
    A strobe node that renders solid colors from the color scheme.
    Responds strongly to strobe signals with rapid color flashing.
    """

    def __init__(
        self,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
        strobe_frequency: float = 8.0,  # Flashes per second during strobe
        signal: FrameSignal = FrameSignal.strobe,
    ):
        """
        Args:
            width: Width of the rendered rectangle
            height: Height of the rendered rectangle
            strobe_frequency: Number of color flashes per second during strobe
            signal: Primary signal to respond to (default: strobe)
        """
        super().__init__([])
        self.width = width
        self.height = height
        self.strobe_frequency = strobe_frequency
        self.signal = signal

        # State tracking
        self.current_color = (0.0, 0.0, 0.0)  # Start with black
        self.last_strobe_time = 0.0
        self.strobe_color_index = 0

        # Color cycling for strobe effects
        self.strobe_colors = []  # Will be populated from color scheme

        # OpenGL resources
        self.framebuffer = None
        self.texture = None
        self.shader_program = None
        self.quad_vao = None

    def enter(self, context: mgl.Context):
        """Initialize GL resources"""
        self._setup_gl_resources(context)

    def exit(self):
        """Clean up GL resources"""
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
        """Configure strobe parameters based on the vibe"""
        # Adjust strobe frequency based on mode
        if vibe.mode == Mode.rave:
            # High energy: faster strobing
            self.strobe_frequency = 12.0
        elif vibe.mode == Mode.gentle:
            # Medium energy: normal strobing
            self.strobe_frequency = 8.0
        elif vibe.mode == Mode.blackout:
            # Low energy: slower strobing (though blackout typically means no visuals)
            self.strobe_frequency = 4.0

    def _setup_gl_resources(self, context: mgl.Context):
        """Setup OpenGL resources for rendering a solid color rectangle"""
        if not self.texture:
            self.texture = context.texture((self.width, self.height), 3)  # RGB
            self.framebuffer = context.framebuffer(color_attachments=[self.texture])

        if not self.shader_program:
            vertex_shader = """
            #version 330 core
            in vec2 in_position;
            
            void main() {
                gl_Position = vec4(in_position, 0.0, 1.0);
            }
            """

            fragment_shader = """
            #version 330 core
            out vec3 color;
            uniform vec3 u_color;
            uniform float u_opacity;
            
            void main() {
                color = u_color * u_opacity;
            }
            """

            self.shader_program = context.program(
                vertex_shader=vertex_shader, fragment_shader=fragment_shader
            )

        if not self.quad_vao:
            # Create fullscreen quad vertices
            vertices = [
                -1.0,
                -1.0,  # Bottom-left
                1.0,
                -1.0,  # Bottom-right
                -1.0,
                1.0,  # Top-left
                1.0,
                1.0,  # Top-right
            ]

            import numpy as np

            vertices_array = np.array(vertices, dtype=np.float32)
            vbo = context.buffer(vertices_array.tobytes())
            self.quad_vao = context.vertex_array(
                self.shader_program, [(vbo, "2f", "in_position")]
            )

    def _update_strobe_colors(self, scheme: ColorScheme):
        """Update the strobe color palette from the color scheme"""
        # Extract RGB values from color scheme (already in 0-1 range)
        fg_rgb = scheme.fg.rgb
        bg_rgb = scheme.bg.rgb
        bg_contrast_rgb = scheme.bg_contrast.rgb

        # Create a palette of colors for strobing
        self.strobe_colors = [
            fg_rgb,  # Primary foreground color
            bg_contrast_rgb,  # Contrast color
            (1.0, 1.0, 1.0),  # White for maximum flash
            fg_rgb,  # Repeat primary for emphasis
            (0.0, 0.0, 0.0),  # Black for contrast
            bg_contrast_rgb,  # Repeat contrast
        ]

    def _get_strobe_color(self, current_time: float) -> Tuple[float, float, float]:
        """Get the current strobe color based on timing"""
        if not self.strobe_colors:
            return (1.0, 1.0, 1.0)  # Default to white if no colors set

        # Calculate which color to show based on strobe frequency
        strobe_period = 1.0 / self.strobe_frequency
        color_index = int((current_time / strobe_period) % len(self.strobe_colors))
        return self.strobe_colors[color_index]

    def render(
        self, frame: Frame, scheme: ColorScheme, context: mgl.Context
    ) -> mgl.Framebuffer:
        """Render the strobe effect"""
        if not self.framebuffer:
            self._setup_gl_resources(context)

        # Update color palette from scheme
        self._update_strobe_colors(scheme)

        current_time = time.time()

        # Get signal values
        strobe_value = frame[FrameSignal.strobe]
        big_blinder_value = frame[FrameSignal.big_blinder]
        primary_signal_value = frame[self.signal]

        # Determine color and opacity based on signals
        color = (0.0, 0.0, 0.0)  # Default to black (invisible)
        opacity = 0.0

        # STROBE: Primary response - rapid color flashing
        if strobe_value > 0.5:
            color = self._get_strobe_color(current_time)
            # Create rapid on/off flashing within each color
            flash_cycle = (current_time * self.strobe_frequency * 2.0) % 1.0
            opacity = 1.0 if flash_cycle < 0.5 else 0.0
            opacity *= strobe_value  # Scale by signal strength

        # BIG BLINDER: Solid white flash
        elif big_blinder_value > 0.5:
            color = (1.0, 1.0, 1.0)  # Pure white
            opacity = big_blinder_value

        # Primary signal: Subtle color presence
        elif primary_signal_value > 0.3:
            # Use a subtle version of the foreground color
            color = scheme.fg.rgb
            opacity = primary_signal_value * 0.3  # Keep it subtle

        # Store current color for consistency
        self.current_color = color

        # Render
        self.framebuffer.use()
        context.clear(0.0, 0.0, 0.0)  # Clear to black

        # Set uniforms and render quad
        self.shader_program["u_color"] = color
        self.shader_program["u_opacity"] = opacity
        self.quad_vao.render(mgl.TRIANGLE_STRIP)

        return self.framebuffer
