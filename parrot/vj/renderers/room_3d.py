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
from parrot.utils.input_events import InputEvents


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
        self.camera_distance = 10  # Distance from center
        self.camera_height = 2.0  # Height above floor
        self.camera_angle = 0.0  # Current rotation angle (radians) - horizontal
        self.camera_tilt = (
            0.3  # Tilt angle (radians) - vertical (0 = level, positive = looking down)
        )
        self.camera_rotation_sensitivity = 0.005  # Radians per pixel of mouse drag
        self.camera_tilt_sensitivity = 0.005  # Radians per pixel of vertical drag
        self.camera_zoom_sensitivity = 0.5  # Units per scroll tick

        # Camera constraints
        self.min_camera_distance = 3.0
        self.max_camera_distance = 30.0
        self.min_camera_tilt = -0.5  # Can't look too far up
        self.max_camera_tilt = 1.4  # Can't look too far down

        # Register for mouse events
        self.input_events = InputEvents.get_instance()
        self.input_events.register_mouse_drag_callback(self._on_mouse_drag)
        self.input_events.register_mouse_scroll_callback(self._on_mouse_scroll)

        # Floor grid parameters
        self.grid_size = 1.0  # Size of each grid square
        self.floor_color = (0.1, 0.1, 0.1)  # Dark floor
        self.grid_color = (0.25, 0.25, 0.25)  # Darker grey gridlines

        # Lighting setup
        # Directional light from top down
        self.directional_light_dir = np.array([0.0, -1.0, 0.0], dtype=np.float32)
        self.directional_light_color = np.array([0.4, 0.4, 0.4], dtype=np.float32)

        # Point light from center of room
        self.point_light_pos = np.array([0.0, 2.0, 0.0], dtype=np.float32)
        self.point_light_color = np.array([0.8, 0.8, 0.8], dtype=np.float32)

        # Material properties
        self.ambient_strength = 0.3
        self.specular_strength = 0.5
        self.floor_specular_strength = 0.1  # Lower specular for floor
        self.shininess = 32.0

        self._setup_shaders()
        self._setup_floor_geometry()

    def _setup_shaders(self):
        """Setup OpenGL shaders for 3D rendering with Blinn-Phong lighting"""
        self.shader = self.ctx.program(
            vertex_shader="""
                #version 330 core
                in vec3 position;
                in vec3 color;
                in vec3 normal;
                
                uniform mat4 mvp;
                uniform mat4 model;
                
                out vec3 frag_pos;
                out vec3 frag_color;
                out vec3 frag_normal;
                
                void main() {
                    vec4 pos = mvp * vec4(position, 1.0);
                    pos.y = -pos.y;  // Flip Y axis
                    gl_Position = pos;
                    frag_pos = vec3(model * vec4(position, 1.0));
                    frag_color = color;
                    frag_normal = mat3(model) * normal;
                }
            """,
            fragment_shader="""
                #version 330 core
                in vec3 frag_pos;
                in vec3 frag_color;
                in vec3 frag_normal;
                
                out vec4 color;
                
                // Lighting uniforms
                uniform vec3 viewPos;
                uniform vec3 dirLightDir;
                uniform vec3 dirLightColor;
                uniform vec3 pointLightPos;
                uniform vec3 pointLightColor;
                uniform float ambientStrength;
                uniform float specularStrength;
                uniform float shininess;
                uniform float emission;  // 0.0 = normal lighting, 1.0 = full emission
                
                void main() {
                    // If emission is high, just use the color directly (emissive)
                    if (emission > 0.5) {
                        color = vec4(frag_color, 1.0);
                    } else {
                        // Normal lighting calculations
                        vec3 norm = normalize(frag_normal);
                        vec3 viewDir = normalize(viewPos - frag_pos);
                        
                        // Ambient
                        vec3 ambient = ambientStrength * frag_color;
                        
                        // Directional light (Blinn-Phong)
                        vec3 lightDir = normalize(-dirLightDir);
                        float diff = max(dot(norm, lightDir), 0.0);
                        vec3 diffuse = diff * dirLightColor * frag_color;
                        
                        vec3 halfwayDir = normalize(lightDir + viewDir);
                        float spec = pow(max(dot(norm, halfwayDir), 0.0), shininess);
                        vec3 specular = specularStrength * spec * dirLightColor;
                        
                        // Point light (Blinn-Phong)
                        vec3 pointLightDir = normalize(pointLightPos - frag_pos);
                        float pointDiff = max(dot(norm, pointLightDir), 0.0);
                        float distance = length(pointLightPos - frag_pos);
                        float attenuation = 1.0 / (1.0 + 0.09 * distance + 0.032 * distance * distance);
                        vec3 pointDiffuse = pointDiff * pointLightColor * frag_color * attenuation;
                        
                        vec3 pointHalfway = normalize(pointLightDir + viewDir);
                        float pointSpec = pow(max(dot(norm, pointHalfway), 0.0), shininess);
                        vec3 pointSpecular = specularStrength * pointSpec * pointLightColor * attenuation;
                        
                        // Combine lighting
                        vec3 result = ambient + diffuse + specular + pointDiffuse + pointSpecular;
                        color = vec4(result, 1.0);
                    }
                }
            """,
        )

    def _setup_floor_geometry(self):
        """Create floor grid geometry with normals"""
        # Floor quad vertices (dark)
        back_left = (-5.0, 0.0, -5.0)
        back_right = (5.0, 0.0, -5.0)
        front_left = (-5.0, 0.0, 5.0)
        front_right = (5.0, 0.0, 5.0)

        # Floor normal (pointing up)
        floor_normal = (0.0, 1.0, 0.0)

        # Floor quad (two triangles)
        floor_vertices = [
            back_left,
            back_right,
            front_left,  # First triangle
            back_right,
            front_right,
            front_left,  # Second triangle
        ]

        floor_normals = [floor_normal] * 6
        floor_colors = [self.floor_color] * 6

        # Convert to flat arrays
        floor_verts_flat = []
        floor_norms_flat = []
        floor_cols_flat = []

        for vert, norm, col in zip(floor_vertices, floor_normals, floor_colors):
            floor_verts_flat.extend(vert)
            floor_norms_flat.extend(norm)
            floor_cols_flat.extend(col)

        # Create VBO and VAO for floor
        self.floor_vertices = np.array(floor_verts_flat, dtype=np.float32)
        self.floor_normals = np.array(floor_norms_flat, dtype=np.float32)
        self.floor_colors = np.array(floor_cols_flat, dtype=np.float32)

        self.floor_vbo = self.ctx.buffer(self.floor_vertices.tobytes())
        self.floor_normal_vbo = self.ctx.buffer(self.floor_normals.tobytes())
        self.floor_color_vbo = self.ctx.buffer(self.floor_colors.tobytes())

        self.floor_vao = self.ctx.vertex_array(
            self.shader,
            [
                (self.floor_vbo, "3f", "position"),
                (self.floor_color_vbo, "3f", "color"),
                (self.floor_normal_vbo, "3f", "normal"),
            ],
        )

        # Create grid lines (grey)
        grid_lines = self._create_grid_lines()
        grid_verts = []
        grid_cols = []
        grid_norms = []

        for line in grid_lines:
            # Start point
            grid_verts.extend(line[:3])
            grid_cols.extend(self.grid_color)
            grid_norms.extend(floor_normal)
            # End point
            grid_verts.extend(line[3:])
            grid_cols.extend(self.grid_color)
            grid_norms.extend(floor_normal)

        self.grid_vertices = np.array(grid_verts, dtype=np.float32)
        self.grid_colors = np.array(grid_cols, dtype=np.float32)
        self.grid_normals = np.array(grid_norms, dtype=np.float32)

        self.grid_vbo = self.ctx.buffer(self.grid_vertices.tobytes())
        self.grid_color_vbo = self.ctx.buffer(self.grid_colors.tobytes())
        self.grid_normal_vbo = self.ctx.buffer(self.grid_normals.tobytes())

        self.grid_vao = self.ctx.vertex_array(
            self.shader,
            [
                (self.grid_vbo, "3f", "position"),
                (self.grid_color_vbo, "3f", "color"),
                (self.grid_normal_vbo, "3f", "normal"),
            ],
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
        # Use proper perspective projection
        fov = 60.0  # Field of view in degrees
        aspect = self.width / self.height  # Aspect ratio
        near = 0.1
        far = 100.0

        # Convert FOV to radians
        fov_rad = math.radians(fov)
        f = 1.0 / math.tan(fov_rad / 2.0)

        # Perspective projection matrix
        proj = np.array(
            [
                [f / aspect, 0, 0, 0],
                [0, f, 0, 0],
                [0, 0, (far + near) / (near - far), (2 * far * near) / (near - far)],
                [0, 0, -1, 0],
            ],
            dtype=np.float32,
        )

        # Calculate camera position based on rotation angle and tilt
        # Camera orbits around the center at (0, 0, 0)
        # Apply tilt by adjusting the vertical position based on tilt angle
        horizontal_distance = self.camera_distance * math.cos(self.camera_tilt)
        cam_x = horizontal_distance * math.sin(self.camera_angle)
        cam_z = horizontal_distance * math.cos(self.camera_angle)
        cam_y = self.camera_height + self.camera_distance * math.sin(self.camera_tilt)

        # Create view matrix using lookAt approach
        # Camera position
        eye = np.array([cam_x, cam_y, cam_z])
        # Look at center of room (slightly above floor for better view)
        center = np.array([0.0, self.camera_height * 0.5, 0.0])
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

    def _on_mouse_drag(self, dx: float, dy: float):
        """Handle mouse drag to rotate and tilt camera"""
        # Horizontal drag rotates around Y axis
        self.camera_angle -= dx * self.camera_rotation_sensitivity

        # Vertical drag tilts camera up/down
        self.camera_tilt += dy * self.camera_tilt_sensitivity

        # Clamp tilt to prevent looking too far up or down
        self.camera_tilt = max(
            self.min_camera_tilt, min(self.max_camera_tilt, self.camera_tilt)
        )

    def _on_mouse_scroll(self, scroll_x: float, scroll_y: float):
        """Handle mouse scroll to zoom camera in/out"""
        # Scroll up = zoom in (decrease distance), scroll down = zoom out (increase distance)
        self.camera_distance -= scroll_y * self.camera_zoom_sensitivity

        # Clamp distance to prevent getting too close or too far
        self.camera_distance = max(
            self.min_camera_distance,
            min(self.max_camera_distance, self.camera_distance),
        )

    def update_camera(self, time: float):
        """Update camera - no longer auto-rotates, controlled by mouse"""
        # Camera angle is now controlled by mouse drag
        pass

    def render_floor(self):
        """Render the floor quad and grid lines with lighting"""
        mvp = self._get_mvp_matrix()
        model = np.eye(4, dtype=np.float32)

        # Calculate camera position for lighting (same as in _get_mvp_matrix)
        horizontal_distance = self.camera_distance * math.cos(self.camera_tilt)
        cam_x = horizontal_distance * math.sin(self.camera_angle)
        cam_z = horizontal_distance * math.cos(self.camera_angle)
        cam_y = self.camera_height + self.camera_distance * math.sin(self.camera_tilt)
        view_pos = np.array([cam_x, cam_y, cam_z], dtype=np.float32)

        # Set uniforms
        self.shader["mvp"] = mvp.T.flatten()
        self.shader["model"] = model.T.flatten()
        self.shader["viewPos"] = tuple(view_pos)
        self.shader["dirLightDir"] = tuple(self.directional_light_dir)
        self.shader["dirLightColor"] = tuple(self.directional_light_color)
        self.shader["pointLightPos"] = tuple(self.point_light_pos)
        self.shader["pointLightColor"] = tuple(self.point_light_color)
        self.shader["ambientStrength"] = self.ambient_strength
        self.shader["specularStrength"] = (
            self.floor_specular_strength
        )  # Lower specular for floor
        self.shader["shininess"] = self.shininess
        self.shader["emission"] = 0.0  # Floor uses normal lighting

        # Render dark floor quad
        self.floor_vao.render(mgl.TRIANGLES)

        # Render grey grid lines on top
        self.grid_vao.render(mgl.LINES)

    def render_fixture_cube(
        self,
        x: float,
        y: float,
        z: float,
        color: tuple[float, float, float],
        size: float = 0.5,
    ):
        """Render a 3D cube for a fixture with normals and lighting"""
        # Create cube vertices
        half_size = size / 2.0

        # Define cube faces with normals
        # Front face (normal: 0, 0, -1)
        front = [
            [x - half_size, y, z - half_size],
            [x + half_size, y, z - half_size],
            [x - half_size, y + size, z - half_size],
            [x + half_size, y, z - half_size],
            [x + half_size, y + size, z - half_size],
            [x - half_size, y + size, z - half_size],
        ]
        front_normal = [0.0, 0.0, -1.0]

        # Back face (normal: 0, 0, 1)
        back = [
            [x - half_size, y, z + half_size],
            [x - half_size, y + size, z + half_size],
            [x + half_size, y, z + half_size],
            [x + half_size, y, z + half_size],
            [x - half_size, y + size, z + half_size],
            [x + half_size, y + size, z + half_size],
        ]
        back_normal = [0.0, 0.0, 1.0]

        # Left face (normal: -1, 0, 0)
        left = [
            [x - half_size, y, z - half_size],
            [x - half_size, y + size, z - half_size],
            [x - half_size, y, z + half_size],
            [x - half_size, y, z + half_size],
            [x - half_size, y + size, z - half_size],
            [x - half_size, y + size, z + half_size],
        ]
        left_normal = [-1.0, 0.0, 0.0]

        # Right face (normal: 1, 0, 0)
        right = [
            [x + half_size, y, z - half_size],
            [x + half_size, y, z + half_size],
            [x + half_size, y + size, z - half_size],
            [x + half_size, y + size, z - half_size],
            [x + half_size, y, z + half_size],
            [x + half_size, y + size, z + half_size],
        ]
        right_normal = [1.0, 0.0, 0.0]

        # Top face (normal: 0, 1, 0)
        top = [
            [x - half_size, y + size, z - half_size],
            [x + half_size, y + size, z - half_size],
            [x - half_size, y + size, z + half_size],
            [x + half_size, y + size, z - half_size],
            [x + half_size, y + size, z + half_size],
            [x - half_size, y + size, z + half_size],
        ]
        top_normal = [0.0, 1.0, 0.0]

        # Bottom face (normal: 0, -1, 0)
        bottom = [
            [x - half_size, y, z - half_size],
            [x - half_size, y, z + half_size],
            [x + half_size, y, z - half_size],
            [x + half_size, y, z - half_size],
            [x - half_size, y, z + half_size],
            [x + half_size, y, z + half_size],
        ]
        bottom_normal = [0.0, -1.0, 0.0]

        # Combine all faces
        cube_vertices = []
        cube_normals = []
        for face, normal in [
            (front, front_normal),
            (back, back_normal),
            (left, left_normal),
            (right, right_normal),
            (top, top_normal),
            (bottom, bottom_normal),
        ]:
            for vertex in face:
                cube_vertices.extend(vertex)
                cube_normals.extend(normal)

        # Create colors (same color for all vertices)
        num_vertices = len(cube_vertices) // 3
        cube_colors = []
        for _ in range(num_vertices):
            cube_colors.extend(color)

        # Create VBOs
        vertices_array = np.array(cube_vertices, dtype=np.float32)
        normals_array = np.array(cube_normals, dtype=np.float32)
        colors_array = np.array(cube_colors, dtype=np.float32)

        vbo = self.ctx.buffer(vertices_array.tobytes())
        normal_vbo = self.ctx.buffer(normals_array.tobytes())
        color_vbo = self.ctx.buffer(colors_array.tobytes())

        vao = self.ctx.vertex_array(
            self.shader,
            [
                (vbo, "3f", "position"),
                (color_vbo, "3f", "color"),
                (normal_vbo, "3f", "normal"),
            ],
        )

        # Set uniforms (reuse from render_floor)
        mvp = self._get_mvp_matrix()
        model = np.eye(4, dtype=np.float32)

        horizontal_distance = self.camera_distance * math.cos(self.camera_tilt)
        cam_x = horizontal_distance * math.sin(self.camera_angle)
        cam_z = horizontal_distance * math.cos(self.camera_angle)
        cam_y = self.camera_height + self.camera_distance * math.sin(self.camera_tilt)
        view_pos = np.array([cam_x, cam_y, cam_z], dtype=np.float32)

        self.shader["mvp"] = mvp.T.flatten()
        self.shader["model"] = model.T.flatten()
        self.shader["viewPos"] = tuple(view_pos)
        self.shader["emission"] = 0.0  # Fixture bodies use normal lighting

        # Render cube
        vao.render(mgl.TRIANGLES)

        # Cleanup
        vbo.release()
        normal_vbo.release()
        color_vbo.release()
        vao.release()

    def render_rectangular_box(
        self,
        x: float,
        y: float,
        z: float,
        color: tuple[float, float, float],
        width: float,
        height: float,
        depth: float,
    ):
        """Render a rectangular box (not a cube) with custom dimensions"""
        half_width = width / 2.0
        half_height = height / 2.0
        half_depth = depth / 2.0

        # Define box faces with normals (similar to cube but with custom dimensions)
        # Front face (normal: 0, 0, -1)
        front = [
            [x - half_width, y, z - half_depth],
            [x + half_width, y, z - half_depth],
            [x - half_width, y + height, z - half_depth],
            [x + half_width, y, z - half_depth],
            [x + half_width, y + height, z - half_depth],
            [x - half_width, y + height, z - half_depth],
        ]
        front_normal = [0.0, 0.0, -1.0]

        # Back face (normal: 0, 0, 1)
        back = [
            [x - half_width, y, z + half_depth],
            [x - half_width, y + height, z + half_depth],
            [x + half_width, y, z + half_depth],
            [x + half_width, y, z + half_depth],
            [x - half_width, y + height, z + half_depth],
            [x + half_width, y + height, z + half_depth],
        ]
        back_normal = [0.0, 0.0, 1.0]

        # Left face (normal: -1, 0, 0)
        left = [
            [x - half_width, y, z - half_depth],
            [x - half_width, y + height, z - half_depth],
            [x - half_width, y, z + half_depth],
            [x - half_width, y, z + half_depth],
            [x - half_width, y + height, z - half_depth],
            [x - half_width, y + height, z + half_depth],
        ]
        left_normal = [-1.0, 0.0, 0.0]

        # Right face (normal: 1, 0, 0)
        right = [
            [x + half_width, y, z - half_depth],
            [x + half_width, y, z + half_depth],
            [x + half_width, y + height, z - half_depth],
            [x + half_width, y + height, z - half_depth],
            [x + half_width, y, z + half_depth],
            [x + half_width, y + height, z + half_depth],
        ]
        right_normal = [1.0, 0.0, 0.0]

        # Top face (normal: 0, 1, 0)
        top = [
            [x - half_width, y + height, z - half_depth],
            [x + half_width, y + height, z - half_depth],
            [x - half_width, y + height, z + half_depth],
            [x + half_width, y + height, z - half_depth],
            [x + half_width, y + height, z + half_depth],
            [x - half_width, y + height, z + half_depth],
        ]
        top_normal = [0.0, 1.0, 0.0]

        # Bottom face (normal: 0, -1, 0)
        bottom = [
            [x - half_width, y, z - half_depth],
            [x - half_width, y, z + half_depth],
            [x + half_width, y, z - half_depth],
            [x + half_width, y, z - half_depth],
            [x - half_width, y, z + half_depth],
            [x + half_width, y, z + half_depth],
        ]
        bottom_normal = [0.0, -1.0, 0.0]

        # Combine all faces
        box_vertices = []
        box_normals = []
        for face, normal in [
            (front, front_normal),
            (back, back_normal),
            (left, left_normal),
            (right, right_normal),
            (top, top_normal),
            (bottom, bottom_normal),
        ]:
            for vertex in face:
                box_vertices.extend(vertex)
                box_normals.extend(normal)

        # Create colors (same color for all vertices)
        num_vertices = len(box_vertices) // 3
        box_colors = []
        for _ in range(num_vertices):
            box_colors.extend(color)

        # Create VBOs
        vertices_array = np.array(box_vertices, dtype=np.float32)
        normals_array = np.array(box_normals, dtype=np.float32)
        colors_array = np.array(box_colors, dtype=np.float32)

        vbo = self.ctx.buffer(vertices_array.tobytes())
        normal_vbo = self.ctx.buffer(normals_array.tobytes())
        color_vbo = self.ctx.buffer(colors_array.tobytes())

        vao = self.ctx.vertex_array(
            self.shader,
            [
                (vbo, "3f", "position"),
                (color_vbo, "3f", "color"),
                (normal_vbo, "3f", "normal"),
            ],
        )

        # Set uniforms
        mvp = self._get_mvp_matrix()
        model = np.eye(4, dtype=np.float32)

        horizontal_distance = self.camera_distance * math.cos(self.camera_tilt)
        cam_x = horizontal_distance * math.sin(self.camera_angle)
        cam_z = horizontal_distance * math.cos(self.camera_angle)
        cam_y = self.camera_height + self.camera_distance * math.sin(self.camera_tilt)
        view_pos = np.array([cam_x, cam_y, cam_z], dtype=np.float32)

        self.shader["mvp"] = mvp.T.flatten()
        self.shader["model"] = model.T.flatten()
        self.shader["viewPos"] = tuple(view_pos)
        self.shader["emission"] = 0.0  # Rectangular boxes use normal lighting

        # Render box
        vao.render(mgl.TRIANGLES)

        # Cleanup
        vbo.release()
        normal_vbo.release()
        color_vbo.release()
        vao.release()

    def render_sphere(
        self,
        x: float,
        y: float,
        z: float,
        color: tuple[float, float, float],
        radius: float = 0.3,
    ):
        """Render a 3D sphere (approximated with icosahedron for performance)"""
        # Create icosahedron vertices (simple sphere approximation)
        t = (1.0 + math.sqrt(5.0)) / 2.0

        # Base icosahedron vertices
        vertices = [
            [-1, t, 0],
            [1, t, 0],
            [-1, -t, 0],
            [1, -t, 0],
            [0, -1, t],
            [0, 1, t],
            [0, -1, -t],
            [0, 1, -t],
            [t, 0, -1],
            [t, 0, 1],
            [-t, 0, -1],
            [-t, 0, 1],
        ]

        # Normalize and scale
        sphere_vertices = []
        for v in vertices:
            length = math.sqrt(v[0] ** 2 + v[1] ** 2 + v[2] ** 2)
            sphere_vertices.append(
                [
                    x + (v[0] / length) * radius,
                    y + (v[1] / length) * radius,
                    z + (v[2] / length) * radius,
                ]
            )

        # Icosahedron faces (20 triangles)
        faces = [
            [0, 11, 5],
            [0, 5, 1],
            [0, 1, 7],
            [0, 7, 10],
            [0, 10, 11],
            [1, 5, 9],
            [5, 11, 4],
            [11, 10, 2],
            [10, 7, 6],
            [7, 1, 8],
            [3, 9, 4],
            [3, 4, 2],
            [3, 2, 6],
            [3, 6, 8],
            [3, 8, 9],
            [4, 9, 5],
            [2, 4, 11],
            [6, 2, 10],
            [8, 6, 7],
            [9, 8, 1],
        ]

        # Build triangle list
        triangle_vertices = []
        for face in faces:
            triangle_vertices.append(sphere_vertices[face[0]])
            triangle_vertices.append(sphere_vertices[face[1]])
            triangle_vertices.append(sphere_vertices[face[2]])

        # Create colors (same color for all vertices)
        sphere_colors = [color] * len(triangle_vertices)

        # Create VBOs
        vertices_array = np.array(triangle_vertices, dtype=np.float32).flatten()
        colors_array = np.array(sphere_colors, dtype=np.float32).flatten()

        vbo = self.ctx.buffer(vertices_array.tobytes())
        color_vbo = self.ctx.buffer(colors_array.tobytes())

        vao = self.ctx.vertex_array(
            self.shader, [(vbo, "3f", "position"), (color_vbo, "3f", "color")]
        )

        # Render sphere with emission (bulbs glow independently)
        mvp = self._get_mvp_matrix()
        self.shader["mvp"] = mvp.T.flatten()
        self.shader["emission"] = 1.0  # Bulbs are emissive - not affected by lighting
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
        if hasattr(self, "floor_normal_vbo"):
            self.floor_normal_vbo.release()
        if hasattr(self, "floor_color_vbo"):
            self.floor_color_vbo.release()
        if hasattr(self, "floor_vao"):
            self.floor_vao.release()
        if hasattr(self, "grid_vbo"):
            self.grid_vbo.release()
        if hasattr(self, "grid_normal_vbo"):
            self.grid_normal_vbo.release()
        if hasattr(self, "grid_color_vbo"):
            self.grid_color_vbo.release()
        if hasattr(self, "grid_vao"):
            self.grid_vao.release()
