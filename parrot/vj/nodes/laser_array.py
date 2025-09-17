#!/usr/bin/env python3

import numpy as np
import moderngl as mgl
from typing import List, Optional
from beartype import beartype

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
        self.depth_texture = self._context.depth_texture((self.width, self.height))
        self.framebuffer = self._context.framebuffer(
            color_attachments=[self.color_texture], depth_attachment=self.depth_texture
        )

        # Create shaders and geometry
        self._create_shaders()
        self._create_geometry()

    def _create_shaders(self):
        """Create simple shader for white laser line"""
        # Simple laser vertex shader
        laser_vertex = """
        #version 330 core
        in float in_distance;   // 0.0 (start) to 1.0 (end)
        in float in_side;       // -1.0 or +1.0 (left/right)

        uniform mat4 view;
        uniform mat4 projection;
        uniform vec3 view_direction;   // normalized camera forward
        uniform vec3 beam_origin;
        uniform vec3 beam_direction;   // normalized
        uniform float beam_length;
        uniform float beam_half_width;

        void main() {
            // Compute a width vector perpendicular to the beam and camera
            vec3 side_vec = normalize(cross(beam_direction, view_direction));
            // Fallback in case beam is parallel to camera direction
            if (length(side_vec) < 1e-4) {
                side_vec = normalize(cross(beam_direction, vec3(0.0,1.0,0.0)));
            }

            vec3 p = beam_origin
                   + beam_direction * (in_distance * beam_length)
                   + side_vec * (in_side * beam_half_width);

            gl_Position = projection * view * vec4(p, 1.0);
        }
        """

        # Simple white laser fragment shader
        laser_fragment = """
        #version 330 core
        out vec4 color;

        void main() {
            color = vec4(1.0, 1.0, 1.0, 1.0);  // Pure white
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

        indices = np.array([0, 1, 2, 0, 2, 3], dtype=np.uint32)

        vbo = self._context.buffer(vertices.tobytes())
        ibo = self._context.buffer(indices.tobytes())

        self.laser_vao = self._context.vertex_array(
            self.laser_program,
            [(vbo, "1f 1f", "in_distance", "in_side")],
            ibo,
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
        if not self.framebuffer or not self.laser_vao:
            return None

        # Create matrices
        view, projection = self._create_matrices()

        # Render laser to main framebuffer
        self.framebuffer.use()
        context.clear(0.0, 0.0, 0.0, 0.0)  # Transparent background
        context.disable(mgl.DEPTH_TEST)
        context.enable(mgl.BLEND)
        context.blend_func = mgl.SRC_ALPHA, mgl.ONE_MINUS_SRC_ALPHA

        # Render single laser beam straight along laser pointing direction
        laser_direction = self.laser_point_vector / np.linalg.norm(
            self.laser_point_vector
        )

        # Set shader uniforms
        self.laser_program["view"].write(view.astype(np.float32).tobytes())
        self.laser_program["projection"].write(projection.astype(np.float32).tobytes())
        self.laser_program["beam_origin"] = tuple(self.laser_position)
        self.laser_program["beam_direction"] = tuple(laser_direction)
        self.laser_program["beam_length"] = float(self.laser_length)
        self.laser_program["beam_half_width"] = float(self.laser_thickness * 0.5)

        # Approximate camera forward from view matrix
        view_arr = view
        np_forward = -view_arr[2, :3]
        np_forward = np_forward / (np.linalg.norm(np_forward) + 1e-6)
        self.laser_program["view_direction"] = tuple(np_forward)

        # Render laser geometry
        self.laser_vao.render(mgl.TRIANGLES)

        context.disable(mgl.BLEND)
        return self.framebuffer
