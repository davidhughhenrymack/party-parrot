#!/usr/bin/env python3
"""
Shared OpenGL rendering utilities for DMX fixture renderers.
Provides simple shape drawing primitives that fixture renderers can use.
"""

from beartype import beartype
import moderngl as mgl
import numpy as np


@beartype
class SimpleShapeRenderer:
    """Helper class for rendering simple 2D shapes in OpenGL"""

    def __init__(self, context: mgl.Context, canvas_width: float, canvas_height: float):
        self.ctx = context
        self.canvas_width = canvas_width
        self.canvas_height = canvas_height

        # Create shader for simple shapes
        self.shader = self.ctx.program(
            vertex_shader="""
                #version 330
                in vec2 in_position;
                uniform vec2 canvas_size;
                
                void main() {
                    // Convert from canvas coordinates to clip space (-1 to 1)
                    vec2 normalized = in_position / canvas_size;
                    vec2 clip_pos = normalized * 2.0 - 1.0;
                    // Flip Y since canvas Y goes down but OpenGL Y goes up
                    clip_pos.y = -clip_pos.y;
                    gl_Position = vec4(clip_pos, 0.0, 1.0);
                }
            """,
            fragment_shader="""
                #version 330
                out vec4 fragColor;
                uniform vec3 color;
                uniform float alpha;
                
                void main() {
                    fragColor = vec4(color, alpha);
                }
            """,
        )

        self.shader["canvas_size"] = (canvas_width, canvas_height)

    def draw_rectangle(
        self,
        x: float,
        y: float,
        width: float,
        height: float,
        color: tuple[float, float, float],
        alpha: float = 1.0,
    ):
        """Draw a filled rectangle"""
        # Create vertices for rectangle (two triangles)
        vertices = np.array(
            [
                x,
                y,
                x + width,
                y,
                x,
                y + height,
                x + width,
                y,
                x + width,
                y + height,
                x,
                y + height,
            ],
            dtype="f4",
        )

        vbo = self.ctx.buffer(vertices.tobytes())
        vao = self.ctx.simple_vertex_array(self.shader, vbo, "in_position")

        self.shader["color"] = color
        self.shader["alpha"] = alpha

        vao.render(mgl.TRIANGLES)

        vbo.release()
        vao.release()

    def draw_circle(
        self,
        cx: float,
        cy: float,
        radius: float,
        color: tuple[float, float, float],
        alpha: float = 1.0,
        segments: int = 32,
    ):
        """Draw a filled circle"""
        import math

        # Create vertices for circle (triangle fan)
        vertices = [cx, cy]  # Center point
        for i in range(segments + 1):
            angle = 2.0 * math.pi * i / segments
            x = cx + radius * math.cos(angle)
            y = cy + radius * math.sin(angle)
            vertices.extend([x, y])

        vertices_array = np.array(vertices, dtype="f4")
        vbo = self.ctx.buffer(vertices_array.tobytes())
        vao = self.ctx.simple_vertex_array(self.shader, vbo, "in_position")

        self.shader["color"] = color
        self.shader["alpha"] = alpha

        vao.render(mgl.TRIANGLE_FAN)

        vbo.release()
        vao.release()

    def draw_line(
        self,
        x1: float,
        y1: float,
        x2: float,
        y2: float,
        color: tuple[float, float, float],
        alpha: float = 1.0,
        width: float = 1.0,
    ):
        """Draw a line"""
        vertices = np.array([x1, y1, x2, y2], dtype="f4")
        vbo = self.ctx.buffer(vertices.tobytes())
        vao = self.ctx.simple_vertex_array(self.shader, vbo, "in_position")

        self.shader["color"] = color
        self.shader["alpha"] = alpha

        # Set line width
        self.ctx.line_width = width

        vao.render(mgl.LINES)

        vbo.release()
        vao.release()
