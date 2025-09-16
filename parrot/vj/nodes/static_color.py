#!/usr/bin/env python3

import numpy as np
import moderngl as mgl
from beartype.typing import Tuple
from beartype import beartype

from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.director.frame import Frame
from parrot.director.color_scheme import ColorScheme
from parrot.vj.constants import DEFAULT_WIDTH, DEFAULT_HEIGHT


@beartype
class StaticColor(BaseInterpretationNode[mgl.Context, None, mgl.Framebuffer]):
    """A node that renders a solid color rectangle for testing and backgrounds"""

    def __init__(
        self,
        color: Tuple[float, float, float] = (1.0, 1.0, 1.0),
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
    ):
        """
        Args:
            color: RGB color tuple with values 0.0-1.0 (default: white)
            width: Width of the rendered rectangle
            height: Height of the rendered rectangle
        """
        super().__init__([])
        self.color = color
        self.width = width
        self.height = height

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
        """Nothing to generate for a static color"""
        pass

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
            
            void main() {
                color = u_color;
            }
            """

            self.shader_program = context.program(
                vertex_shader=vertex_shader, fragment_shader=fragment_shader
            )

        if not self.quad_vao:
            # Create fullscreen quad vertices
            vertices = np.array(
                [
                    -1.0,
                    -1.0,  # Bottom-left
                    1.0,
                    -1.0,  # Bottom-right
                    -1.0,
                    1.0,  # Top-left
                    1.0,
                    1.0,  # Top-right
                ],
                dtype=np.float32,
            )

            vbo = context.buffer(vertices.tobytes())
            self.quad_vao = context.vertex_array(
                self.shader_program, [(vbo, "2f", "in_position")]
            )

    def render(
        self, frame: Frame, scheme: ColorScheme, context: mgl.Context
    ) -> mgl.Framebuffer:
        """Render a solid color rectangle"""
        if not self.framebuffer:
            self._setup_gl_resources(context)

        self.framebuffer.use()
        context.clear(0.0, 0.0, 0.0)  # Clear to black

        # Set the color uniform and render quad
        self.shader_program["u_color"] = self.color
        self.quad_vao.render(mgl.TRIANGLE_STRIP)

        return self.framebuffer


# Convenience factory functions for common colors
def White(width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT) -> StaticColor:
    """Create a white StaticColor node"""
    return StaticColor(color=(1.0, 1.0, 1.0), width=width, height=height)


def Red(width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT) -> StaticColor:
    """Create a red StaticColor node"""
    return StaticColor(color=(1.0, 0.0, 0.0), width=width, height=height)


def Green(width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT) -> StaticColor:
    """Create a green StaticColor node"""
    return StaticColor(color=(0.0, 1.0, 0.0), width=width, height=height)


def Blue(width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT) -> StaticColor:
    """Create a blue StaticColor node"""
    return StaticColor(color=(0.0, 0.0, 1.0), width=width, height=height)


def Gray(
    intensity: float = 0.5, width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT
) -> StaticColor:
    """Create a gray StaticColor node with specified intensity"""
    return StaticColor(
        color=(intensity, intensity, intensity), width=width, height=height
    )
