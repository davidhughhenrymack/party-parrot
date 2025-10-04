#!/usr/bin/env python3
"""
3D room renderer for DMX fixtures.
Creates a room perspective with floor grid and 3D fixture cubes.
"""

from beartype import beartype
import moderngl as mgl
import numpy as np
import math
from typing import Optional

from parrot.fixtures.base import FixtureBase
from parrot.vj.renderers.base import FixtureRenderer
from parrot.director.frame import Frame


@beartype
class Room3DRenderer:
    """3D room renderer with floor grid and 3D fixture cubes"""

    def __init__(self, context: mgl.Context, width: int, height: int):
        self.ctx = context
        self.width = width
        self.height = height

        # Room dimensions (in arbitrary units)
        self.room_width = 20.0  # Stage to back wall
        self.room_depth = 15.0  # Left to right
        self.stage_depth = 3.0  # How deep the stage is

        # Camera setup - looking from audience towards stage
        self.camera_distance = 7.0  # Distance from center (closer to room)
        self.camera_height = (
            2.5  # Height above floor (slightly elevated for better view)
        )
        self.camera_rotation_speed = 0.1  # Radians per second
        self.camera_angle = 0.0  # Current rotation angle

        # Floor grid parameters
        self.grid_size = 1.0  # Size of each grid square
        self.floor_color = (0.3, 0.3, 0.3)  # Gray floor

        self._setup_shaders()
        self._setup_floor_geometry()

    def _setup_shaders(self):
        """Setup OpenGL shaders for 3D rendering"""
        self.shader = self.ctx.program(
            vertex_shader="""
                #version 330 core
                in vec3 position;
                in vec3 color;
                
                uniform mat4 mvp;
                
                out vec3 frag_color;
                
                void main() {
                    gl_Position = mvp * vec4(position, 1.0);
                    frag_color = color;
                }
            """,
            fragment_shader="""
                #version 330 core
                in vec3 frag_color;
                out vec4 color;
                
                void main() {
                    color = vec4(frag_color, 1.0);
                }
            """,
        )

    def _setup_floor_geometry(self):
        """Create floor grid geometry"""
        # Create floor vertices with grid lines
        vertices = []
        colors = []

        # Floor quad (simple rectangle for now)
        # Make it visible in orthographic projection
        back_left = (-5.0, 0.0, -5.0)
        back_right = (5.0, 0.0, -5.0)
        front_left = (-5.0, 0.0, 5.0)
        front_right = (5.0, 0.0, 5.0)

        # Floor quad (two triangles)
        floor_vertices = [
            back_left,
            back_right,
            front_left,  # First triangle
            back_right,
            front_right,
            front_left,  # Second triangle
        ]

        for vertex in floor_vertices:
            vertices.extend(vertex)
            colors.extend(self.floor_color)

        # Add grid lines
        grid_lines = self._create_grid_lines()
        for line in grid_lines:
            vertices.extend(line[:3])
            colors.extend(self.floor_color)
            vertices.extend(line[3:])
            colors.extend(self.floor_color)

        # Create VBO and VAO for floor
        self.floor_vertices = np.array(vertices, dtype=np.float32)
        self.floor_colors = np.array(colors, dtype=np.float32)

        self.floor_vbo = self.ctx.buffer(self.floor_vertices.tobytes())
        self.floor_color_vbo = self.ctx.buffer(self.floor_colors.tobytes())

        self.floor_vao = self.ctx.vertex_array(
            self.shader,
            [(self.floor_vbo, "3f", "position"), (self.floor_color_vbo, "3f", "color")],
        )

    def _create_grid_lines(self):
        """Create grid lines for the floor"""
        lines = []

        # Simple grid lines in visible range
        # Horizontal lines (across the floor)
        for i in range(-5, 6):
            lines.append([-5.0, 0.001, i, 5.0, 0.001, i])

        # Vertical lines (along the floor)
        for i in range(-5, 6):
            lines.append([i, 0.001, -5.0, i, 0.001, 5.0])

        return lines

    def _get_mvp_matrix(self):
        """Calculate Model-View-Projection matrix for camera perspective"""
        # Use orthographic projection for now to debug
        # This will make objects visible regardless of depth
        left = -10.0
        right = 10.0
        bottom = -10.0
        top = 10.0
        near = 0.1
        far = 100.0

        # Orthographic projection matrix
        proj = np.array(
            [
                [2.0 / (right - left), 0, 0, -(right + left) / (right - left)],
                [0, 2.0 / (top - bottom), 0, -(top + bottom) / (top - bottom)],
                [0, 0, -2.0 / (far - near), -(far + near) / (far - near)],
                [0, 0, 0, 1],
            ],
            dtype=np.float32,
        )

        # Calculate camera position based on rotation angle
        # Camera orbits around the center at (0, 0, 0)
        cam_x = self.camera_distance * math.sin(self.camera_angle)
        cam_z = self.camera_distance * math.cos(self.camera_angle)
        cam_y = self.camera_height

        # Create view matrix using lookAt approach
        # Camera position
        eye = np.array([cam_x, cam_y, cam_z])
        # Look at center of room
        center = np.array([0.0, 0.0, 0.0])
        # Up vector
        up = np.array([0.0, 1.0, 0.0])

        # Calculate view matrix
        view = self._create_look_at_matrix(eye, center, up)

        # Model matrix (identity for now)
        model = np.eye(4, dtype=np.float32)

        # MVP = Projection * View * Model
        mvp = proj @ view @ model
        return mvp

    def _create_look_at_matrix(self, eye, center, up):
        """Create a look-at view matrix"""
        # Forward vector (from eye to center)
        f = center - eye
        f = f / np.linalg.norm(f)

        # Right vector
        s = np.cross(f, up)
        s = s / np.linalg.norm(s)

        # Up vector (recalculate to ensure orthogonality)
        u = np.cross(s, f)

        # Create view matrix
        view = np.array(
            [
                [s[0], s[1], s[2], -np.dot(s, eye)],
                [u[0], u[1], u[2], -np.dot(u, eye)],
                [-f[0], -f[1], -f[2], np.dot(f, eye)],
                [0, 0, 0, 1],
            ],
            dtype=np.float32,
        )
        return view

    def update_camera(self, time: float):
        """Update camera rotation based on time"""
        self.camera_angle = time * self.camera_rotation_speed

    def render_floor(self):
        """Render the floor grid"""
        mvp = self._get_mvp_matrix()
        self.shader["mvp"] = mvp.T.flatten()

        # Render floor quad
        self.floor_vao.render(mgl.TRIANGLES, vertices=6)

        # Render grid lines
        self.floor_vao.render(mgl.LINES, vertices=len(self.floor_vertices) // 3 - 6)

    def render_fixture_cube(
        self,
        x: float,
        y: float,
        z: float,
        color: tuple[float, float, float],
        size: float = 0.5,
    ):
        """Render a 3D cube for a fixture"""
        # Create cube vertices
        half_size = size / 2.0
        cube_vertices = [
            # Front face
            [x - half_size, y, z - half_size],
            [x + half_size, y, z - half_size],
            [x - half_size, y + size, z - half_size],
            [x + half_size, y, z - half_size],
            [x + half_size, y + size, z - half_size],
            [x - half_size, y + size, z - half_size],
            # Back face
            [x - half_size, y, z + half_size],
            [x - half_size, y + size, z + half_size],
            [x + half_size, y, z + half_size],
            [x + half_size, y, z + half_size],
            [x - half_size, y + size, z + half_size],
            [x + half_size, y + size, z + half_size],
            # Left face
            [x - half_size, y, z - half_size],
            [x - half_size, y + size, z - half_size],
            [x - half_size, y, z + half_size],
            [x - half_size, y, z + half_size],
            [x - half_size, y + size, z - half_size],
            [x - half_size, y + size, z + half_size],
            # Right face
            [x + half_size, y, z - half_size],
            [x + half_size, y, z + half_size],
            [x + half_size, y + size, z - half_size],
            [x + half_size, y + size, z - half_size],
            [x + half_size, y, z + half_size],
            [x + half_size, y + size, z + half_size],
            # Top face
            [x - half_size, y + size, z - half_size],
            [x + half_size, y + size, z - half_size],
            [x - half_size, y + size, z + half_size],
            [x + half_size, y + size, z - half_size],
            [x + half_size, y + size, z + half_size],
            [x - half_size, y + size, z + half_size],
            # Bottom face
            [x - half_size, y, z - half_size],
            [x - half_size, y, z + half_size],
            [x + half_size, y, z - half_size],
            [x + half_size, y, z - half_size],
            [x - half_size, y, z + half_size],
            [x + half_size, y, z + half_size],
        ]

        # Create colors (same color for all vertices)
        cube_colors = [color] * len(cube_vertices)

        # Create VBOs
        vertices_array = np.array(cube_vertices, dtype=np.float32).flatten()
        colors_array = np.array(cube_colors, dtype=np.float32).flatten()

        vbo = self.ctx.buffer(vertices_array.tobytes())
        color_vbo = self.ctx.buffer(colors_array.tobytes())

        vao = self.ctx.vertex_array(
            self.shader, [(vbo, "3f", "position"), (color_vbo, "3f", "color")]
        )

        # Render cube
        mvp = self._get_mvp_matrix()
        self.shader["mvp"] = mvp.T.flatten()
        vao.render(mgl.TRIANGLES)

        # Cleanup
        vbo.release()
        color_vbo.release()
        vao.release()

    def convert_2d_to_3d(
        self, x: float, y: float, canvas_width: float, canvas_height: float
    ):
        """Convert 2D canvas coordinates to 3D room coordinates

        Maps fixture positions from [0-500] range to floor space [-5 to 5]
        """
        # Assume fixtures are positioned in a [0-500] coordinate system
        # Map to floor space which is [-5 to 5] in both X and Z
        fixture_coord_range = 500.0
        floor_size = 10.0  # Floor goes from -5 to 5

        # Normalize to [0-1] range assuming [0-500] input
        norm_x = x / fixture_coord_range
        norm_y = y / fixture_coord_range

        # Convert to room coordinates in visible range
        # X: left-right in room (-5 to 5)
        room_x = (norm_x - 0.5) * floor_size

        # Z: depth in room (-5 to 5)
        # Y coordinate from canvas becomes Z depth (forward/back)
        room_z = (norm_y - 0.5) * floor_size

        # Y: height above floor (cubes sit on floor)
        room_y = 0.0

        return room_x, room_y, room_z

    def cleanup(self):
        """Clean up OpenGL resources"""
        if hasattr(self, "floor_vbo"):
            self.floor_vbo.release()
        if hasattr(self, "floor_color_vbo"):
            self.floor_color_vbo.release()
        if hasattr(self, "floor_vao"):
            self.floor_vao.release()
