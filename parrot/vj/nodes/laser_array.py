#!/usr/bin/env python3

import numpy as np
import moderngl as mgl
from typing import List, Optional
from beartype import beartype
import math

from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.director.frame import Frame
from parrot.director.color_scheme import ColorScheme
from parrot.vj.constants import DEFAULT_WIDTH, DEFAULT_HEIGHT
from parrot.vj.utils.math_3d import (
    look_at_matrix,
    perspective_matrix,
)


@beartype
class LaserBeam:
    """Individual laser beam state"""

    def __init__(self, beam_id: int, fan_angle: float):
        self.beam_id = beam_id
        self.fan_angle = fan_angle  # Angle within the fan for this beam
        self.intensity = 1.0


@beartype
class LaserArray(BaseInterpretationNode[mgl.Context, None, mgl.Framebuffer]):
    """
    Simplified 3D laser array that projects N lasers from a single point.
    Lasers fan out in a 2D plane based on quaternion rotation and Frame signals.
    """

    def __init__(
        self,
        camera_eye: np.ndarray,
        camera_target: np.ndarray,
        camera_up: np.ndarray,
        laser_position: np.ndarray,
        laser_point_vector: np.ndarray,
        laser_count: int = 1,  # Single beam only
        laser_length: float = 40.0,
        laser_thickness: float = 10.0,  # 10px wide
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
    ):
        """
        Args:
            camera_eye: Camera position (from ConcertStage)
            camera_target: Camera target (from ConcertStage)
            camera_up: Camera up vector (from ConcertStage)
            laser_position: 3D position of laser source
            laser_point_vector: Primary direction vector the laser unit points at
            laser_count: Number of laser beams (default 30)
            laser_length: Length of each laser beam
            laser_thickness: Base thickness of laser beams
            width: Render target width
            height: Render target height
        """
        super().__init__([])

        # Camera system (never moves)
        self.camera_eye = camera_eye.copy()
        self.camera_target = camera_target.copy()
        self.camera_up = camera_up.copy()

        # Laser system
        self.laser_position = laser_position.copy()
        self.laser_point_vector = laser_point_vector.copy()
        self.laser_count = laser_count
        self.laser_length = laser_length
        self.laser_thickness = laser_thickness
        self.width = width
        self.height = height

        # Create single laser beam
        self.lasers: List[LaserBeam] = []
        self._setup_lasers()

        # OpenGL resources
        self._context: Optional[mgl.Context] = None
        self.framebuffer: Optional[mgl.Framebuffer] = None
        self.color_texture: Optional[mgl.Texture] = None
        self.depth_texture: Optional[mgl.Texture] = None

        # Shaders and geometry
        self.laser_program: Optional[mgl.Program] = None
        self.laser_vao: Optional[mgl.VertexArray] = None

    def _setup_lasers(self):
        """Create single laser beam"""
        self.lasers = [LaserBeam(0, 0.0)]  # Single beam pointing straight

    def enter(self, context: mgl.Context):
        """Initialize OpenGL resources"""
        self._context = context
        self._setup_gl_resources()

    def exit(self):
        """Clean up OpenGL resources"""
        resources = [
            self.framebuffer,
            self.color_texture,
            self.depth_texture,
            self.laser_program,
            self.laser_vao,
        ]

        for resource in resources:
            if resource:
                resource.release()

        self._context = None

    def generate(self, vibe: Vibe):
        """Generate new laser configuration - simplified to do nothing"""
        pass

    def _setup_gl_resources(self):
        """Setup OpenGL resources for laser rendering"""
        if not self._context:
            return

        # Create main framebuffer
        self.color_texture = self._context.texture((self.width, self.height), 4)
        self.framebuffer = self._context.framebuffer(
            color_attachments=[self.color_texture]
        )

        # Create shaders and geometry
        self._create_shaders()
        self._create_geometry()

    def _create_shaders(self):
        """Create shader for tapered, soft-edged laser strip"""
        # Vertex shader (debug): draw a strip in NDC to validate pipeline
        laser_vertex = """
        #version 330 core
        in float in_distance;   // 0.0 (start) to 1.0 (end)
        in float in_side;       // -1.0 or +1.0 (left/right)

        void main() {
            // Map attributes directly to NDC for visibility
            float x = in_side * 0.3;              // width
            float y = mix(-0.2, 0.6, in_distance); // height from -0.2 to 0.6
            gl_Position = vec4(x, y, 0.0, 1.0);
        }
        """

        # Fragment shader: output solid color (debug). We'll refine to soft edges once visible.
        laser_fragment = """
        #version 330 core
        out vec4 color;

        void main() {
            color = vec4(1.0, 1.0, 1.0, 1.0);
        }
        """

        self.laser_program = self._context.program(
            vertex_shader=laser_vertex, fragment_shader=laser_fragment
        )

    def _create_geometry(self):
        """Create geometry for laser beam"""
        # Create a unit quad with attributes: in_distance (0/1) and in_side (-1/+1)
        # Vertex order: (start,-1), (start,+1), (end,+1), (end,-1)
        vertices = np.array(
            [
                # in_distance, in_side
                0.0,
                -1.0,
                0.0,
                1.0,
                1.0,
                1.0,
                1.0,
                -1.0,
            ],
            dtype=np.float32,
        )

        vbo = self._context.buffer(vertices.tobytes())

        # Use a triangle strip without an index buffer for simplicity
        self.laser_vao = self._context.vertex_array(
            self.laser_program,
            [(vbo, "1f 1f", "in_distance", "in_side")],
        )

    def _create_matrices(self):
        """Create view and projection matrices using camera system"""
        # Use camera system from ConcertStage (never moves)
        view = look_at_matrix(self.camera_eye, self.camera_target, self.camera_up)

        # Projection matrix
        aspect = self.width / self.height
        projection = perspective_matrix(45.0, aspect, 0.1, 100.0)

        return view, projection

    def render(
        self, frame: Frame, scheme: ColorScheme, context: mgl.Context
    ) -> Optional[mgl.Framebuffer]:
        """Render simple white laser beam"""
        if not self.framebuffer or not self.color_texture:
            return None

        # Create matrices
        view, projection = self._create_matrices()

        # Clear framebuffer
        self.framebuffer.use()
        context.viewport = (0, 0, self.width, self.height)
        context.clear(0.0, 0.0, 0.0, 0.0)

        # CPU rasterization fallback: draw multiple straight lines (lasers)
        buf = np.zeros((self.height, self.width, 4), dtype=np.uint8)

        # Base direction toward audience
        d = self.laser_point_vector
        if np.linalg.norm(d) < 1e-6:
            d = self.camera_eye - self.laser_position
        base_dir = d / (np.linalg.norm(d) + 1e-6)

        # Derived parameters
        num_beams = max(1, self.laser_count)
        half = (num_beams - 1) * 0.5
        fan_angle = np.radians(50.0)
        thickness_px = max(1, int(self.laser_thickness))

        time_s = float(getattr(frame, "time", 0.0))
        sweep = math.sin(time_s * 0.8) * (fan_angle * 0.3)

        def project(point3: np.ndarray):
            p = np.append(point3.astype(np.float32), 1.0)
            clip = projection @ (view @ p)
            if abs(float(clip[3])) < 1e-6:
                return None
            ndc = clip[:3] / clip[3]
            x = int((ndc[0] * 0.5 + 0.5) * (self.width - 1))
            y = int((ndc[1] * 0.5 + 0.5) * (self.height - 1))
            return x, y

        origin = self.laser_position

        for i in range(num_beams):
            factor = (i - half) / max(1.0, half if half != 0 else 1.0)
            angle = factor * fan_angle + sweep

            # Rotate base_dir around Y axis
            cos_a = math.cos(angle)
            sin_a = math.sin(angle)
            dir_x = base_dir[0] * cos_a + base_dir[2] * sin_a
            dir_z = -base_dir[0] * sin_a + base_dir[2] * cos_a
            dir_vec = np.array([dir_x, base_dir[1], dir_z], dtype=np.float32)
            dir_vec = dir_vec / (np.linalg.norm(dir_vec) + 1e-6)

            end = origin + dir_vec * self.laser_length

            p0 = project(origin)
            p1 = project(end)
            if p0 is None or p1 is None:
                continue

            x0, y0 = p0
            x1, y1 = p1

            # Bresenham-like thick line
            dx = abs(x1 - x0)
            dy = -abs(y1 - y0)
            sx = 1 if x0 < x1 else -1
            sy = 1 if y0 < y1 else -1
            err = dx + dy
            x, y = x0, y0

            while True:
                for tx in range(-thickness_px // 2, thickness_px // 2 + 1):
                    for ty in range(-thickness_px // 2, thickness_px // 2 + 1):
                        xx = x + tx
                        yy = y + ty
                        if 0 <= xx < self.width and 0 <= yy < self.height:
                            buf[yy, xx, 0] = min(255, buf[yy, xx, 0] + 255)
                            buf[yy, xx, 1] = min(255, buf[yy, xx, 1] + 255)
                            buf[yy, xx, 2] = min(255, buf[yy, xx, 2] + 255)
                            buf[yy, xx, 3] = 255

                if x == x1 and y == y1:
                    break
                e2 = 2 * err
                if e2 >= dy:
                    err += dy
                    x += sx
                if e2 <= dx:
                    err += dx
                    y += sy

        # Upload to texture
        self.color_texture.write(buf.tobytes())
        return self.framebuffer
