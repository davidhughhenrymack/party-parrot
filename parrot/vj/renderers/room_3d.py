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
from contextlib import contextmanager
from PIL import Image, ImageDraw, ImageFont

from parrot.fixtures.base import FixtureBase
from parrot.vj.renderers.base import FixtureRenderer
from parrot.director.frame import Frame
from parrot.utils.input_events import InputEvents


@beartype
class Room3DRenderer:
    """3D room renderer with floor grid and 3D fixture cubes"""

    def __init__(
        self, context: mgl.Context, width: int, height: int, show_floor: bool = False
    ):
        self.ctx = context
        self.width = width
        self.height = height
        self.show_floor = show_floor

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
        self._setup_emission_shader()  # Separate shader for pure emission (no lighting)
        self._setup_text_shader()  # Shader for text rendering with texture

        # Only setup floor geometry if enabled
        if self.show_floor:
            self._setup_floor_geometry()

        # Transform stacks for hierarchical rendering
        self.position_stack: list[tuple[float, float, float]] = [(0.0, 0.0, 0.0)]
        self.rotation_stack: list[np.ndarray] = [self._identity_quaternion()]

        # Text rendering cache
        self._text_texture_cache: dict[str, mgl.Texture] = {}
        self._text_font: Optional[ImageFont.ImageFont] = None
        self._load_text_font()

        # Geometry cache for reusable shapes
        self._cube_cache: dict[
            float, tuple[mgl.Buffer, mgl.Buffer, mgl.Buffer, mgl.VertexArray, int]
        ] = {}
        self._circle_cache: dict[
            tuple[float, int],
            tuple[mgl.Buffer, mgl.Buffer, mgl.Buffer, mgl.VertexArray, int],
        ] = {}
        self._cone_cache: dict[
            tuple[float, float, int],
            tuple[mgl.Buffer, mgl.Buffer, mgl.VertexArray, int],
        ] = {}

    def _setup_shaders(self):
        """Setup OpenGL shaders for 3D rendering with Blinn-Phong lighting"""
        self.shader = self.ctx.program(
            vertex_shader="""
                #version 330 core
                in vec3 position;
                in vec4 color;
                in vec3 normal;
                
                uniform mat4 mvp;
                uniform mat4 model;
                
                out vec3 frag_pos;
                out vec4 frag_color;
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
                in vec4 frag_color;
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
                    // Use >= to be more robust
                    if (emission >= 0.99) {
                        // Pure emission - use color directly without any lighting
                        color = frag_color;
                    } else {
                        // Normal lighting calculations
                        vec3 norm = normalize(frag_normal);
                        vec3 viewDir = normalize(viewPos - frag_pos);
                        
                        // Ambient
                        vec3 ambient = ambientStrength * frag_color.rgb;
                        
                        // Directional light (Blinn-Phong)
                        vec3 lightDir = normalize(-dirLightDir);
                        float diff = max(dot(norm, lightDir), 0.0);
                        vec3 diffuse = diff * dirLightColor * frag_color.rgb;
                        
                        vec3 halfwayDir = normalize(lightDir + viewDir);
                        float spec = pow(max(dot(norm, halfwayDir), 0.0), shininess);
                        vec3 specular = specularStrength * spec * dirLightColor;
                        
                        // Point light (Blinn-Phong)
                        vec3 pointLightDir = normalize(pointLightPos - frag_pos);
                        float pointDiff = max(dot(norm, pointLightDir), 0.0);
                        float distance = length(pointLightPos - frag_pos);
                        float attenuation = 1.0 / (1.0 + 0.09 * distance + 0.032 * distance * distance);
                        vec3 pointDiffuse = pointDiff * pointLightColor * frag_color.rgb * attenuation;
                        
                        vec3 pointHalfway = normalize(pointLightDir + viewDir);
                        float pointSpec = pow(max(dot(norm, pointHalfway), 0.0), shininess);
                        vec3 pointSpecular = specularStrength * pointSpec * pointLightColor * attenuation;
                        
                        // Combine lighting
                        vec3 result = ambient + diffuse + specular + pointDiffuse + pointSpecular;
                        color = vec4(result, frag_color.a);  // Preserve alpha from input
                    }
                }
            """,
        )

    def _setup_emission_shader(self):
        """Setup pure emission shader with NO lighting calculations"""
        self.emission_shader = self.ctx.program(
            vertex_shader="""
                #version 330 core
                in vec3 position;
                in vec4 color;
                
                uniform mat4 mvp;
                
                out vec4 frag_color;
                
                void main() {
                    vec4 pos = mvp * vec4(position, 1.0);
                    pos.y = -pos.y;  // Flip Y axis
                    gl_Position = pos;
                    frag_color = color;  // Just pass through color
                }
            """,
            fragment_shader="""
                #version 330 core
                in vec4 frag_color;
                out vec4 color;
                
                void main() {
                    // Pure emission - just output the color directly, no lighting
                    color = frag_color;
                }
            """,
        )

    def _setup_text_shader(self):
        """Setup shader for text rendering with texture"""
        self.text_shader = self.ctx.program(
            vertex_shader="""
                #version 330 core
                in vec3 position;
                in vec2 texcoord;
                
                uniform mat4 mvp;
                
                out vec2 uv;
                
                void main() {
                    vec4 pos = mvp * vec4(position, 1.0);
                    pos.y = -pos.y;  // Flip Y axis
                    gl_Position = pos;
                    uv = texcoord;
                }
            """,
            fragment_shader="""
                #version 330 core
                in vec2 uv;
                out vec4 color;
                
                uniform sampler2D text_texture;
                uniform vec3 text_color;
                
                void main() {
                    // Sample text alpha from texture (white text on black background)
                    float alpha = texture(text_texture, uv).r;
                    // Output colored text with transparency
                    color = vec4(text_color, alpha);
                }
            """,
        )

    def _load_text_font(self):
        """Load a simple font for text rendering"""
        try:
            # Try to load a simple monospace font
            self._text_font = ImageFont.truetype("Courier", 12)
        except (OSError, IOError):
            try:
                # Try system font paths
                import os

                font_paths = [
                    "/System/Library/Fonts/Courier.dfont",  # macOS
                    "/System/Library/Fonts/Monaco.dfont",  # macOS
                    "/usr/share/fonts/truetype/dejavu/DejaVuSansMono.ttf",  # Linux
                ]
                for path in font_paths:
                    if os.path.exists(path):
                        self._text_font = ImageFont.truetype(path, 12)
                        break
                else:
                    # Fallback to default
                    self._text_font = ImageFont.load_default()
            except Exception:
                # Final fallback
                self._text_font = ImageFont.load_default()

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
        floor_colors_rgb = [self.floor_color] * 6

        # Convert to flat arrays with RGBA
        floor_verts_flat = []
        floor_norms_flat = []
        floor_cols_flat = []

        for vert, norm, col in zip(floor_vertices, floor_normals, floor_colors_rgb):
            floor_verts_flat.extend(vert)
            floor_norms_flat.extend(norm)
            floor_cols_flat.extend([col[0], col[1], col[2], 1.0])  # Add alpha=1.0

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
                (self.floor_color_vbo, "4f", "color"),
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
            grid_cols.extend(
                [self.grid_color[0], self.grid_color[1], self.grid_color[2], 1.0]
            )
            grid_norms.extend(floor_normal)
            # End point
            grid_verts.extend(line[3:])
            grid_cols.extend(
                [self.grid_color[0], self.grid_color[1], self.grid_color[2], 1.0]
            )
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
                (self.grid_color_vbo, "4f", "color"),
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

    # Transform stack methods

    def _identity_quaternion(self) -> np.ndarray:
        """Return identity quaternion (no rotation)"""
        return np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32)

    def _quaternion_to_matrix(self, q: np.ndarray) -> np.ndarray:
        """Convert quaternion to 4x4 rotation matrix"""
        x, y, z, w = q
        return np.array(
            [
                [
                    1 - 2 * y * y - 2 * z * z,
                    2 * x * y - 2 * w * z,
                    2 * x * z + 2 * w * y,
                    0,
                ],
                [
                    2 * x * y + 2 * w * z,
                    1 - 2 * x * x - 2 * z * z,
                    2 * y * z - 2 * w * x,
                    0,
                ],
                [
                    2 * x * z - 2 * w * y,
                    2 * y * z + 2 * w * x,
                    1 - 2 * x * x - 2 * y * y,
                    0,
                ],
                [0, 0, 0, 1],
            ],
            dtype=np.float32,
        )

    def _get_current_model_matrix(self) -> np.ndarray:
        """Get the current model matrix from transform stacks"""
        # Start with identity
        model = np.eye(4, dtype=np.float32)

        # Apply position translation
        pos = self.position_stack[-1]
        translation = np.array(
            [[1, 0, 0, pos[0]], [0, 1, 0, pos[1]], [0, 0, 1, pos[2]], [0, 0, 0, 1]],
            dtype=np.float32,
        )

        # Apply rotation
        rotation = self._quaternion_to_matrix(self.rotation_stack[-1])

        # Combine: model = translation * rotation
        model = translation @ rotation

        return model

    @contextmanager
    def local_position(self, position: tuple[float, float, float]):
        """Context manager for local position transform

        Usage:
            with room_renderer.local_position((x, y, z)):
                # Render at this position
                room_renderer.render_cube((0, 0, 0), color, size)
        """
        # Push new position onto stack
        self.position_stack.append(position)
        try:
            yield
        finally:
            # Pop position from stack
            self.position_stack.pop()

    def _quaternion_multiply(self, q1: np.ndarray, q2: np.ndarray) -> np.ndarray:
        """Multiply two quaternions to compose rotations"""
        x1, y1, z1, w1 = q1
        x2, y2, z2, w2 = q2
        return np.array(
            [
                w1 * x2 + x1 * w2 + y1 * z2 - z1 * y2,
                w1 * y2 - x1 * z2 + y1 * w2 + z1 * x2,
                w1 * z2 + x1 * y2 - y1 * x2 + z1 * w2,
                w1 * w2 - x1 * x2 - y1 * y2 - z1 * z2,
            ],
            dtype=np.float32,
        )

    @contextmanager
    def local_rotation(self, quaternion: np.ndarray):
        """Context manager for local rotation transform

        Composes with the current rotation on the stack.

        Usage:
            with room_renderer.local_rotation(quat):
                # Render with this rotation
                room_renderer.render_sphere((0, 0, 0.5), color, radius)
        """
        # Compose new rotation with current rotation
        current_rotation = self.rotation_stack[-1]
        composed_rotation = self._quaternion_multiply(current_rotation, quaternion)

        # Push composed rotation onto stack
        self.rotation_stack.append(composed_rotation)
        try:
            yield
        finally:
            # Pop rotation from stack
            self.rotation_stack.pop()

    def render_floor(self):
        """Render the floor quad and grid lines with lighting"""
        if not self.show_floor:
            return

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
        # self.grid_vao.render(mgl.LINES)

    def _create_cube_geometry(self, size: float):
        """Create reusable cube geometry at origin"""
        half_size = size / 2.0

        # Define cube faces with normals (at origin, no position offset)
        front_normal = [0.0, 0.0, -1.0]
        back_normal = [0.0, 0.0, 1.0]
        left_normal = [-1.0, 0.0, 0.0]
        right_normal = [1.0, 0.0, 0.0]
        top_normal = [0.0, 1.0, 0.0]
        bottom_normal = [0.0, -1.0, 0.0]

        # Front face
        front = [
            [-half_size, 0, -half_size],
            [half_size, 0, -half_size],
            [-half_size, size, -half_size],
            [half_size, 0, -half_size],
            [half_size, size, -half_size],
            [-half_size, size, -half_size],
        ]

        # Back face
        back = [
            [-half_size, 0, half_size],
            [-half_size, size, half_size],
            [half_size, 0, half_size],
            [half_size, 0, half_size],
            [-half_size, size, half_size],
            [half_size, size, half_size],
        ]

        # Left face
        left = [
            [-half_size, 0, -half_size],
            [-half_size, size, -half_size],
            [-half_size, 0, half_size],
            [-half_size, 0, half_size],
            [-half_size, size, -half_size],
            [-half_size, size, half_size],
        ]

        # Right face
        right = [
            [half_size, 0, -half_size],
            [half_size, 0, half_size],
            [half_size, size, -half_size],
            [half_size, size, -half_size],
            [half_size, 0, half_size],
            [half_size, size, half_size],
        ]

        # Top face
        top = [
            [-half_size, size, -half_size],
            [half_size, size, -half_size],
            [-half_size, size, half_size],
            [half_size, size, -half_size],
            [half_size, size, half_size],
            [-half_size, size, half_size],
        ]

        # Bottom face
        bottom = [
            [-half_size, 0, -half_size],
            [-half_size, 0, half_size],
            [half_size, 0, -half_size],
            [half_size, 0, -half_size],
            [-half_size, 0, half_size],
            [half_size, 0, half_size],
        ]

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

        vertices_array = np.array(cube_vertices, dtype=np.float32)
        normals_array = np.array(cube_normals, dtype=np.float32)

        vbo = self.ctx.buffer(vertices_array.tobytes())
        normal_vbo = self.ctx.buffer(normals_array.tobytes())

        # Create a per-vertex color VBO that will be updated per render
        num_vertices = len(cube_vertices) // 3
        color_vbo = self.ctx.buffer(
            reserve=num_vertices * 4 * 4
        )  # 4 floats (RGBA) per vertex

        vao = self.ctx.vertex_array(
            self.shader,
            [
                (vbo, "3f", "position"),
                (color_vbo, "4f", "color"),
                (normal_vbo, "3f", "normal"),
            ],
        )

        return vbo, normal_vbo, color_vbo, vao, num_vertices

    def render_cube(
        self,
        position: tuple[float, float, float],
        color: tuple[float, float, float],
        size: float = 0.5,
    ):
        """Render a 3D cube with normals and lighting in local coordinates

        Args:
            position: Local position (x, y, z) relative to current transform
            color: RGB color tuple
            size: Size of the cube
        """
        # Get or create cached geometry
        if size not in self._cube_cache:
            self._cube_cache[size] = self._create_cube_geometry(size)

        vbo, normal_vbo, color_vbo, vao, num_vertices = self._cube_cache[size]

        # Update color buffer with current color
        cube_colors = []
        for _ in range(num_vertices):
            cube_colors.extend([color[0], color[1], color[2], 1.0])
        colors_array = np.array(cube_colors, dtype=np.float32)
        color_vbo.write(colors_array.tobytes())

        # Create translation matrix for position
        x, y, z = position
        local_model = np.array(
            [[1, 0, 0, x], [0, 1, 0, y], [0, 0, 1, z], [0, 0, 0, 1]],
            dtype=np.float32,
        )

        # Combine with current transform stack
        model = self._get_current_model_matrix() @ local_model

        horizontal_distance = self.camera_distance * math.cos(self.camera_tilt)
        cam_x = horizontal_distance * math.sin(self.camera_angle)
        cam_z = horizontal_distance * math.cos(self.camera_angle)
        cam_y = self.camera_height + self.camera_distance * math.sin(self.camera_tilt)
        view_pos = np.array([cam_x, cam_y, cam_z], dtype=np.float32)

        # Compute MVP with model transform
        mvp_with_model = self._get_mvp_matrix() @ model

        self.shader["mvp"] = mvp_with_model.T.flatten()
        self.shader["model"] = model.T.flatten()
        self.shader["viewPos"] = tuple(view_pos)
        self.shader["emission"] = 0.0  # Fixture bodies use normal lighting

        # Render cube (no cleanup - buffers are cached)
        vao.render(mgl.TRIANGLES)

    # Backward compatibility alias
    def render_fixture_cube(
        self,
        x: float,
        y: float,
        z: float,
        color: tuple[float, float, float],
        size: float = 0.5,
    ):
        """Legacy method - use render_cube with local_position context manager instead"""
        with self.local_position((x, y, z)):
            self.render_cube((0.0, 0.0, 0.0), color, size)

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

        # Create colors (same color for all vertices) with alpha=1.0
        num_vertices = len(box_vertices) // 3
        box_colors = []
        for _ in range(num_vertices):
            box_colors.extend([color[0], color[1], color[2], 1.0])

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
                (color_vbo, "4f", "color"),
                (normal_vbo, "3f", "normal"),
            ],
        )

        # Set uniforms using current model matrix from transform stack
        model = self._get_current_model_matrix()
        mvp_with_model = self._get_mvp_matrix() @ model

        horizontal_distance = self.camera_distance * math.cos(self.camera_tilt)
        cam_x = horizontal_distance * math.sin(self.camera_angle)
        cam_z = horizontal_distance * math.cos(self.camera_angle)
        cam_y = self.camera_height + self.camera_distance * math.sin(self.camera_tilt)
        view_pos = np.array([cam_x, cam_y, cam_z], dtype=np.float32)

        self.shader["mvp"] = mvp_with_model.T.flatten()
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

    def _create_circle_geometry(self, radius: float, segments: int):
        """Create reusable circle geometry at origin facing +Z"""
        circle_vertices = []
        circle_normals = []

        # Center point at origin
        center = [0.0, 0.0, 0.0]
        normal = [0.0, 0.0, 1.0]  # Facing +Z

        # Generate circle points and triangles
        for i in range(segments):
            angle1 = 2.0 * math.pi * i / segments
            angle2 = 2.0 * math.pi * ((i + 1) % segments) / segments

            cos1, sin1 = math.cos(angle1), math.sin(angle1)
            cos2, sin2 = math.cos(angle2), math.sin(angle2)

            # Point 1 on circle (in XY plane)
            point1 = [cos1 * radius, sin1 * radius, 0.0]
            # Point 2 on circle
            point2 = [cos2 * radius, sin2 * radius, 0.0]

            # Triangle: center -> point1 -> point2
            circle_vertices.extend(center)
            circle_vertices.extend(point1)
            circle_vertices.extend(point2)

            # All normals point in +Z direction
            for _ in range(3):
                circle_normals.extend(normal)

        vertices_array = np.array(circle_vertices, dtype=np.float32)
        normals_array = np.array(circle_normals, dtype=np.float32)

        vbo = self.ctx.buffer(vertices_array.tobytes())
        normal_vbo = self.ctx.buffer(normals_array.tobytes())

        # Create a per-vertex color VBO that will be updated per render
        num_vertices = len(circle_vertices) // 3
        color_vbo = self.ctx.buffer(
            reserve=num_vertices * 4 * 4
        )  # 4 floats (RGBA) per vertex

        vao = self.ctx.vertex_array(
            self.shader,
            [
                (vbo, "3f", "position"),
                (color_vbo, "4f", "color"),
                (normal_vbo, "3f", "normal"),
            ],
        )

        return vbo, normal_vbo, color_vbo, vao, num_vertices

    def render_circle(
        self,
        position: tuple[float, float, float],
        color: tuple[float, float, float],
        radius: float = 0.3,
        normal: tuple[float, float, float] = (0.0, 0.0, 1.0),
        alpha: float = 1.0,
        segments: int = 24,
    ):
        """Render a flat circular disc in local coordinates

        Args:
            position: Local position (x, y, z) relative to current transform
            color: RGB color tuple
            radius: Radius of the circle
            normal: Normal direction the circle faces (default: +Z, toward audience)
            alpha: Alpha transparency (0.0 = fully transparent, 1.0 = fully opaque)
            segments: Number of segments around the circle
        """
        # Get or create cached geometry
        cache_key = (radius, segments)
        if cache_key not in self._circle_cache:
            self._circle_cache[cache_key] = self._create_circle_geometry(
                radius, segments
            )

        vbo, normal_vbo, color_vbo, vao, num_vertices = self._circle_cache[cache_key]

        # Update color buffer with current color and alpha
        circle_colors = []
        for _ in range(num_vertices):
            circle_colors.extend([color[0], color[1], color[2], alpha])
        colors_array = np.array(circle_colors, dtype=np.float32)
        color_vbo.write(colors_array.tobytes())

        # Create transform to orient circle to face the desired normal
        x, y, z = position
        nx, ny, nz = normal

        # Normalize the normal vector
        normal_length = math.sqrt(nx * nx + ny * ny + nz * nz)
        if normal_length < 0.001:
            nx, ny, nz = 0.0, 0.0, 1.0
        else:
            nx, ny, nz = nx / normal_length, ny / normal_length, nz / normal_length

        # Build rotation matrix to align +Z to desired normal
        # Simple approach: if normal is close to +Z, use identity
        if abs(nz - 1.0) < 0.001:
            # Already facing +Z
            rotation = np.eye(4, dtype=np.float32)
        else:
            # Create perpendicular vectors
            if abs(nx) < 0.9:
                perp1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
            else:
                perp1 = np.array([0.0, 1.0, 0.0], dtype=np.float32)

            normal_vec = np.array([nx, ny, nz], dtype=np.float32)
            perp1 = perp1 - normal_vec * np.dot(perp1, normal_vec)
            perp1 = perp1 / np.linalg.norm(perp1)

            perp2 = np.cross(normal_vec, perp1)
            perp2 = perp2 / np.linalg.norm(perp2)

            # Build rotation matrix from basis vectors
            rotation = np.array(
                [
                    [perp1[0], perp2[0], nx, 0],
                    [perp1[1], perp2[1], ny, 0],
                    [perp1[2], perp2[2], nz, 0],
                    [0, 0, 0, 1],
                ],
                dtype=np.float32,
            )

        # Create translation matrix
        translation = np.array(
            [[1, 0, 0, x], [0, 1, 0, y], [0, 0, 1, z], [0, 0, 0, 1]],
            dtype=np.float32,
        )

        # Combine transforms
        local_model = translation @ rotation
        model = self._get_current_model_matrix() @ local_model

        # Render circle with emission (bulbs glow independently)
        mvp_with_model = self._get_mvp_matrix() @ model

        self.shader["mvp"] = mvp_with_model.T.flatten()
        self.shader["model"] = model.T.flatten()
        self.shader["emission"] = 1.0  # Bulbs are emissive - not affected by lighting

        # Enable blending for transparency if alpha < 1.0
        if alpha < 1.0:
            self.ctx.enable(mgl.BLEND)
            self.ctx.blend_func = mgl.SRC_ALPHA, mgl.ONE_MINUS_SRC_ALPHA

        vao.render(mgl.TRIANGLES)

        # Disable blending
        if alpha < 1.0:
            self.ctx.disable(mgl.BLEND)

    def render_sphere(
        self,
        position: tuple[float, float, float],
        color: tuple[float, float, float],
        radius: float = 0.3,
        alpha: float = 1.0,
    ):
        """Render a 3D sphere (approximated with icosahedron for performance) in local coordinates

        Args:
            position: Local position (x, y, z) relative to current transform
            color: RGB color tuple
            radius: Radius of the sphere
            alpha: Alpha transparency (0.0 = fully transparent, 1.0 = fully opaque)
        """
        x, y, z = position

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

        # Create colors (same color for all vertices) with specified alpha
        sphere_colors = []
        sphere_normals = []
        for vert in triangle_vertices:
            sphere_colors.append([color[0], color[1], color[2], alpha])
            # Calculate normal from vertex position (pointing outward from center)
            dx, dy, dz = vert[0] - x, vert[1] - y, vert[2] - z
            length = math.sqrt(dx * dx + dy * dy + dz * dz)
            if length > 0.001:
                sphere_normals.extend([dx / length, dy / length, dz / length])
            else:
                sphere_normals.extend([0.0, 1.0, 0.0])

        # Create VBOs
        vertices_array = np.array(triangle_vertices, dtype=np.float32).flatten()
        colors_array = np.array(sphere_colors, dtype=np.float32).flatten()
        normals_array = np.array(sphere_normals, dtype=np.float32)

        vbo = self.ctx.buffer(vertices_array.tobytes())
        color_vbo = self.ctx.buffer(colors_array.tobytes())
        normal_vbo = self.ctx.buffer(normals_array.tobytes())

        vao = self.ctx.vertex_array(
            self.shader,
            [
                (vbo, "3f", "position"),
                (color_vbo, "4f", "color"),
                (normal_vbo, "3f", "normal"),
            ],
        )

        # Render sphere with emission (bulbs glow independently)
        model = self._get_current_model_matrix()
        mvp_with_model = self._get_mvp_matrix() @ model

        self.shader["mvp"] = mvp_with_model.T.flatten()
        self.shader["model"] = model.T.flatten()
        self.shader["emission"] = 1.0  # Bulbs are emissive - not affected by lighting

        # Enable blending for transparency if alpha < 1.0
        if alpha < 1.0:
            self.ctx.enable(mgl.BLEND)
            self.ctx.blend_func = mgl.SRC_ALPHA, mgl.ONE_MINUS_SRC_ALPHA

        vao.render(mgl.TRIANGLES)

        # Disable blending
        if alpha < 1.0:
            self.ctx.disable(mgl.BLEND)

        # Cleanup
        vbo.release()
        color_vbo.release()
        normal_vbo.release()
        vao.release()

    def render_bulb_with_beam(
        self,
        position: tuple[float, float, float],
        color: tuple[float, float, float],
        bulb_radius: float = 0.3,
        normal: tuple[float, float, float] = (0.0, 0.0, 1.0),
        alpha: float = 1.0,
        beam_length: float = 5.0,
        beam_alpha: float = 0.15,
    ):
        """Render a bulb (circle) with a cone beam projecting from it

        Args:
            position: Local position (x, y, z) relative to current transform
            color: RGB color tuple
            bulb_radius: Radius of the bulb circle
            normal: Normal direction the bulb faces (default: +Z, toward audience)
            alpha: Alpha transparency for the bulb (0.0 = fully transparent, 1.0 = fully opaque)
            beam_length: Length of the cone beam
            beam_alpha: Alpha transparency for the beam (default: 0.15 for subtle effect)
        """
        # Render the bulb circle
        self.render_circle(position, color, bulb_radius, normal, alpha)

        # Render the cone beam if alpha is significant
        if alpha > 0.05:
            x, y, z = position
            # Beam projects in the same direction as the bulb normal
            self.render_cone_beam(
                x,
                y,
                z,
                normal,
                color,
                length=beam_length,
                start_radius=bulb_radius * 0.3,
                end_radius=bulb_radius * 3.0,
                segments=16,
                alpha=beam_alpha * alpha,  # Scale beam alpha with bulb alpha
            )

    def _create_cone_geometry(
        self, start_radius: float, end_radius: float, segments: int
    ):
        """Create reusable cone geometry along +Z axis from origin to (0, 0, 1)"""
        cone_vertices = []

        # Generate circle points at start (z=0) and end (z=1)
        start_circle = []
        end_circle = []

        for i in range(segments):
            angle = 2.0 * math.pi * i / segments
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)

            # Start circle point (at z=0)
            start_point = [cos_a * start_radius, sin_a * start_radius, 0.0]
            start_circle.append(start_point)

            # End circle point (at z=1, will be scaled by length later)
            end_point = [cos_a * end_radius, sin_a * end_radius, 1.0]
            end_circle.append(end_point)

        # Build triangles for cone surface
        for i in range(segments):
            next_i = (i + 1) % segments

            # Two triangles per segment
            # Triangle 1: start[i], end[i], start[next_i]
            cone_vertices.extend(start_circle[i])
            cone_vertices.extend(end_circle[i])
            cone_vertices.extend(start_circle[next_i])

            # Triangle 2: start[next_i], end[i], end[next_i]
            cone_vertices.extend(start_circle[next_i])
            cone_vertices.extend(end_circle[i])
            cone_vertices.extend(end_circle[next_i])

        vertices_array = np.array(cone_vertices, dtype=np.float32)
        vbo = self.ctx.buffer(vertices_array.tobytes())

        # Create a per-vertex color VBO that will be updated per render
        num_vertices = len(cone_vertices) // 3
        color_vbo = self.ctx.buffer(
            reserve=num_vertices * 4 * 4
        )  # 4 floats (RGBA) per vertex

        vao = self.ctx.vertex_array(
            self.emission_shader,
            [
                (vbo, "3f", "position"),
                (color_vbo, "4f", "color"),
            ],
        )

        return vbo, color_vbo, vao, num_vertices

    def render_cone_beam(
        self,
        start_x: float,
        start_y: float,
        start_z: float,
        direction: tuple[float, float, float],
        color: tuple[float, float, float],
        length: float = 5.0,
        start_radius: float = 0.1,
        end_radius: float = 0.8,
        segments: int = 12,
        alpha: float = 1.0,
    ):
        """Render a cone-shaped light beam projecting in a direction

        Args:
            start_x, start_y, start_z: Starting position of the beam
            direction: Normalized direction vector (dx, dy, dz)
            color: RGB color tuple
            length: Length of the beam
            start_radius: Radius at the start (near light source)
            end_radius: Radius at the end (far from light source)
            segments: Number of segments around the cone circumference
            alpha: Alpha transparency (0.0 = fully transparent, 1.0 = fully opaque)
        """
        # Normalize direction
        dx, dy, dz = direction
        dir_length = math.sqrt(dx * dx + dy * dy + dz * dz)
        if dir_length < 0.001:
            return  # Invalid direction
        dx, dy, dz = dx / dir_length, dy / dir_length, dz / dir_length

        # Get or create cached geometry
        cache_key = (start_radius, end_radius, segments)
        if cache_key not in self._cone_cache:
            self._cone_cache[cache_key] = self._create_cone_geometry(
                start_radius, end_radius, segments
            )

        vbo, color_vbo, vao, num_vertices = self._cone_cache[cache_key]

        # Update color buffer with current color and alpha
        cone_colors = []
        for _ in range(num_vertices):
            cone_colors.extend([color[0], color[1], color[2], alpha])
        colors_array = np.array(cone_colors, dtype=np.float32)
        color_vbo.write(colors_array.tobytes())

        # Build transform to orient cone from origin along +Z to desired position/direction
        # Create perpendicular vectors for the cone orientation
        if abs(dx) < 0.9:
            perp1 = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        else:
            perp1 = np.array([0.0, 1.0, 0.0], dtype=np.float32)

        direction_vec = np.array([dx, dy, dz], dtype=np.float32)
        perp1 = perp1 - direction_vec * np.dot(perp1, direction_vec)
        perp1 = perp1 / np.linalg.norm(perp1)

        perp2 = np.cross(direction_vec, perp1)
        perp2 = perp2 / np.linalg.norm(perp2)

        # Build rotation matrix to align +Z to beam direction
        rotation = np.array(
            [
                [perp1[0], perp2[0], dx, 0],
                [perp1[1], perp2[1], dy, 0],
                [perp1[2], perp2[2], dz, 0],
                [0, 0, 0, 1],
            ],
            dtype=np.float32,
        )

        # Scale matrix for length
        scale = np.array(
            [[1, 0, 0, 0], [0, 1, 0, 0], [0, 0, length, 0], [0, 0, 0, 1]],
            dtype=np.float32,
        )

        # Translation matrix
        translation = np.array(
            [[1, 0, 0, start_x], [0, 1, 0, start_y], [0, 0, 1, start_z], [0, 0, 0, 1]],
            dtype=np.float32,
        )

        # Combine transforms: translate * rotate * scale
        local_model = translation @ rotation @ scale
        model = self._get_current_model_matrix() @ local_model

        # Set uniforms using current model matrix from transform stack
        mvp_with_model = self._get_mvp_matrix() @ model

        # Only need MVP for emission shader (no lighting, no model matrix needed)
        self.emission_shader["mvp"] = mvp_with_model.T.flatten()

        # Enable blending for semi-transparent beams
        self.ctx.enable(mgl.BLEND)
        # Use additive blending so overlapping beams brighten each other
        self.ctx.blend_func = mgl.SRC_ALPHA, mgl.ONE

        # Disable depth writes so beams don't occlude anything behind them
        # But keep depth testing so beams don't render in front of solid objects
        self.ctx.depth_mask = False

        # Render cone (no cleanup - buffers are cached)
        vao.render(mgl.TRIANGLES)

        # Restore depth writes and disable blending
        self.ctx.depth_mask = True
        self.ctx.disable(mgl.BLEND)

    def render_text_label(
        self,
        text: str,
        position: tuple[float, float, float],
        color: tuple[float, float, float] = (1.0, 1.0, 1.0),
        size: float = 0.3,
    ):
        """Render text label at a 3D position

        Args:
            text: Text to render
            position: Local position (x, y, z) relative to current transform
            color: RGB color tuple (0-1 range)
            size: Size of the text quad
        """
        if not self._text_font:
            return

        # Create or get cached texture for this text
        cache_key = text
        if cache_key not in self._text_texture_cache:
            # Create PIL image with text
            # Use a small image size for text labels
            img_width, img_height = 64, 16
            image = Image.new(
                "L", (img_width, img_height), 0
            )  # Grayscale, black background
            draw = ImageDraw.Draw(image)

            # Draw white text
            draw.text((2, 2), text, fill=255, font=self._text_font)

            # Convert to numpy and flip vertically to match OpenGL texture coordinates
            img_array = np.array(image, dtype=np.uint8)
            img_array = np.flipud(img_array)  # Flip to match OpenGL coords
            texture = self.ctx.texture((img_width, img_height), 1, img_array.tobytes())
            texture.filter = (mgl.LINEAR, mgl.LINEAR)
            self._text_texture_cache[cache_key] = texture

        texture = self._text_texture_cache[cache_key]

        # Create a quad to display the text
        x, y, z = position
        aspect = 64.0 / 16.0  # Text texture aspect ratio
        width = size * aspect
        height = size

        # Create quad vertices (billboard facing camera would be ideal, but for now just face forward)
        vertices = [
            [x - width / 2, y, z],
            [x + width / 2, y, z],
            [x - width / 2, y + height, z],
            [x + width / 2, y, z],
            [x + width / 2, y + height, z],
            [x - width / 2, y + height, z],
        ]

        # Texture coordinates
        texcoords = [
            [0.0, 0.0],
            [1.0, 0.0],
            [0.0, 1.0],
            [1.0, 0.0],
            [1.0, 1.0],
            [0.0, 1.0],
        ]

        # Flatten arrays
        vertices_flat = []
        texcoords_flat = []
        for vert, tc in zip(vertices, texcoords):
            vertices_flat.extend(vert)
            texcoords_flat.extend(tc)

        # Create VBOs
        vertices_array = np.array(vertices_flat, dtype=np.float32)
        texcoords_array = np.array(texcoords_flat, dtype=np.float32)

        vbo = self.ctx.buffer(vertices_array.tobytes())
        texcoord_vbo = self.ctx.buffer(texcoords_array.tobytes())

        vao = self.ctx.vertex_array(
            self.text_shader,
            [
                (vbo, "3f", "position"),
                (texcoord_vbo, "2f", "texcoord"),
            ],
        )

        # Set uniforms
        model = self._get_current_model_matrix()
        mvp_with_model = self._get_mvp_matrix() @ model

        self.text_shader["mvp"] = mvp_with_model.T.flatten()
        self.text_shader["text_color"] = color

        # Bind texture and render
        texture.use(0)
        self.text_shader["text_texture"] = 0

        # Enable blending for text transparency
        self.ctx.enable(mgl.BLEND)
        self.ctx.blend_func = mgl.SRC_ALPHA, mgl.ONE_MINUS_SRC_ALPHA

        vao.render(mgl.TRIANGLES)

        # Disable blending
        self.ctx.disable(mgl.BLEND)

        # Cleanup
        vbo.release()
        texcoord_vbo.release()
        vao.release()

    def convert_2d_to_3d(
        self, x: float, y: float, z: float, canvas_width: float, canvas_height: float
    ):
        """Convert 2D canvas coordinates to 3D room coordinates

        Maps fixture positions from [0-500] range to floor space [-5 to 5]
        z parameter controls height above floor
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

        # Y: height above floor (from z parameter)
        room_y = z

        return room_x, room_y, room_z

    def cleanup(self):
        """Clean up OpenGL resources"""
        # Cleanup text textures
        for texture in self._text_texture_cache.values():
            texture.release()
        self._text_texture_cache.clear()

        # Cleanup geometry caches
        for vbo, normal_vbo, color_vbo, vao, _ in self._cube_cache.values():
            vbo.release()
            normal_vbo.release()
            color_vbo.release()
            vao.release()
        self._cube_cache.clear()

        for vbo, normal_vbo, color_vbo, vao, _ in self._circle_cache.values():
            vbo.release()
            normal_vbo.release()
            color_vbo.release()
            vao.release()
        self._circle_cache.clear()

        for vbo, color_vbo, vao, _ in self._cone_cache.values():
            vbo.release()
            color_vbo.release()
            vao.release()
        self._cone_cache.clear()

        # Only cleanup floor resources if they were created
        if self.show_floor:
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
