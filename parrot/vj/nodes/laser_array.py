#!/usr/bin/env python3

import time
import math
import random
import numpy as np
import moderngl as mgl
from typing import List, Optional
from beartype import beartype

from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode
from parrot.vj.constants import DEFAULT_WIDTH, DEFAULT_HEIGHT
from parrot.vj.utils.math_3d import (
    look_at_matrix,
    perspective_matrix,
    create_translation_matrix,
    create_rotation_matrix,
)
from parrot.vj.utils.signal_utils import get_random_frame_signal


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
        laser_count: int = 30,
        laser_length: float = 40.0,  # Longer lasers for better visibility
        laser_thickness: float = 0.1,  # Thicker for better visibility
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

        # Internal quaternion rotation (set on init, for now just identity)
        self.fan_rotation_axis = np.array([0.0, 1.0, 0.0])  # Rotate around Y axis
        self.fan_rotation_angle = 0.0  # No initial rotation

        # Frame signal for fanning (picked randomly on generate)
        self.fan_signal = FrameSignal.freq_high

        # Create laser beams
        self.lasers: List[LaserBeam] = []
        self._setup_lasers()

        # OpenGL resources
        self._context: Optional[mgl.Context] = None
        self.framebuffer: Optional[mgl.Framebuffer] = None
        self.color_texture: Optional[mgl.Texture] = None
        self.depth_texture: Optional[mgl.Texture] = None

        # Bloom effect resources
        self.bloom_framebuffer: Optional[mgl.Framebuffer] = None
        self.bloom_texture: Optional[mgl.Texture] = None
        self.blur_framebuffer1: Optional[mgl.Framebuffer] = None
        self.blur_texture1: Optional[mgl.Texture] = None
        self.blur_framebuffer2: Optional[mgl.Framebuffer] = None
        self.blur_texture2: Optional[mgl.Texture] = None

        # Shaders and geometry
        self.laser_program: Optional[mgl.Program] = None
        self.laser_vao: Optional[mgl.VertexArray] = None
        self.blur_program: Optional[mgl.Program] = None
        self.composite_program: Optional[mgl.Program] = None
        self.quad_vao: Optional[mgl.VertexArray] = None

    def _setup_lasers(self):
        """Create laser beam objects distributed in a fan pattern"""
        self.lasers = []

        for i in range(self.laser_count):
            # Distribute beams evenly across fan angle
            if self.laser_count == 1:
                fan_angle = 0.0
            else:
                # Spread from -45° to +45° (90° total fan)
                fan_range = math.pi / 2  # 90 degrees
                fan_angle = -fan_range / 2 + (fan_range * i / (self.laser_count - 1))

            beam = LaserBeam(i, fan_angle)
            self.lasers.append(beam)

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
            self.bloom_framebuffer,
            self.bloom_texture,
            self.blur_framebuffer1,
            self.blur_texture1,
            self.blur_framebuffer2,
            self.blur_texture2,
            self.laser_program,
            self.laser_vao,
            self.blur_program,
            self.composite_program,
            self.quad_vao,
        ]

        for resource in resources:
            if resource:
                resource.release()

        self._context = None

    def generate(self, vibe: Vibe):
        """Generate new laser configuration based on vibe"""
        # Randomly pick a Frame signal for fanning animation
        self.fan_signal = get_random_frame_signal()

        # Adjust behavior based on mode
        if vibe.mode == Mode.rave:
            # High energy: wider fan, more dynamic
            self.fan_rotation_angle = random.uniform(0, 2 * math.pi)
        elif vibe.mode == Mode.gentle:
            # Calm: narrower fan, less movement
            self.fan_rotation_angle = random.uniform(-math.pi / 4, math.pi / 4)
        elif vibe.mode == Mode.blackout:
            # Minimal activity
            self.fan_rotation_angle = 0.0

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

        # Create bloom framebuffers
        self.bloom_texture = self._context.texture((self.width, self.height), 4)
        self.bloom_framebuffer = self._context.framebuffer(
            color_attachments=[self.bloom_texture]
        )

        # Create blur framebuffers (half resolution for performance)
        blur_width, blur_height = self.width // 2, self.height // 2
        self.blur_texture1 = self._context.texture((blur_width, blur_height), 4)
        self.blur_framebuffer1 = self._context.framebuffer(
            color_attachments=[self.blur_texture1]
        )
        self.blur_texture2 = self._context.texture((blur_width, blur_height), 4)
        self.blur_framebuffer2 = self._context.framebuffer(
            color_attachments=[self.blur_texture2]
        )

        # Create shaders and geometry
        self._create_shaders()
        self._create_geometry()

    def _create_shaders(self):
        """Create shader programs for laser rendering"""
        # Laser vertex shader (billboarded quad per beam)
        laser_vertex = """
        #version 330 core
        in float in_distance;   // 0.0 (start) to 1.0 (end)
        in float in_side;       // -1.0 or +1.0 (left/right)

        uniform mat4 view;
        uniform mat4 projection;
        uniform vec3 camera_position;
        uniform vec3 view_direction;   // normalized camera forward
        uniform vec3 beam_origin;
        uniform vec3 beam_direction;   // normalized
        uniform float beam_length;
        uniform float beam_half_width;

        out vec3 world_pos;
        out float width_from_center;    // 0 at center, 1 at edge
        out float distance_to_camera;

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

            world_pos = p;
            width_from_center = abs(in_side);
            distance_to_camera = length(camera_position - p);

            gl_Position = projection * view * vec4(p, 1.0);
        }
        """

        # Laser fragment shader with 3D thickness and bloom
        laser_fragment = """
        #version 330 core
        in vec3 world_pos;
        in float width_from_center;
        in float distance_to_camera;

        uniform vec3 laser_color;
        uniform float laser_intensity;
        uniform float time;

        out vec4 color;

        void main() {
            // Radial falloff from beam center (crisp core + soft glow)
            float core = 1.0 - smoothstep(0.0, 0.15, width_from_center);
            float glow = 1.0 - smoothstep(0.15, 1.0, width_from_center);
            float beam = core * 1.2 + glow * 0.4;

            // Distance-based attenuation
            float dist = max(0.001, distance_to_camera);
            float distance_falloff = 1.0 / (1.0 + 0.02 * dist);

            // Slight shimmer
            float shimmer = 0.9 + 0.1 * sin(time * 8.0 + world_pos.x * 4.0 + world_pos.z * 4.0);

            float intensity = laser_intensity * beam * distance_falloff * shimmer;
            color = vec4(laser_color * intensity * 2.0, intensity);
        }
        """

        self.laser_program = self._context.program(
            vertex_shader=laser_vertex, fragment_shader=laser_fragment
        )

        # Blur shader for bloom effect
        blur_vertex = """
        #version 330 core
        in vec2 in_position;
        in vec2 in_texcoord;
        
        out vec2 texcoord;
        
        void main() {
            texcoord = in_texcoord;
            gl_Position = vec4(in_position, 0.0, 1.0);
        }
        """

        blur_fragment = """
        #version 330 core
        in vec2 texcoord;
        
        uniform sampler2D input_texture;
        uniform vec2 blur_direction;
        uniform float blur_radius;
        
        out vec4 color;
        
        void main() {
            vec4 result = vec4(0.0);
            vec2 tex_offset = 1.0 / textureSize(input_texture, 0);
            
            // Gaussian blur weights
            float weights[5] = float[](0.227027, 0.1945946, 0.1216216, 0.054054, 0.016216);
            
            result += texture(input_texture, texcoord) * weights[0];
            
            for(int i = 1; i < 5; ++i) {
                vec2 offset = blur_direction * tex_offset * float(i) * blur_radius;
                result += texture(input_texture, texcoord + offset) * weights[i];
                result += texture(input_texture, texcoord - offset) * weights[i];
            }
            
            color = result;
        }
        """

        self.blur_program = self._context.program(
            vertex_shader=blur_vertex, fragment_shader=blur_fragment
        )

        # Composite shader for combining original and bloom
        composite_fragment = """
        #version 330 core
        in vec2 texcoord;
        
        uniform sampler2D original_texture;
        uniform sampler2D bloom_texture;
        uniform float bloom_intensity;
        
        out vec4 color;
        
        void main() {
            vec3 original = texture(original_texture, texcoord).rgb;
            vec3 bloom = texture(bloom_texture, texcoord).rgb;
            
            // Additive bloom
            vec3 result = original + bloom * bloom_intensity;
            
            color = vec4(result, 1.0);
        }
        """

        self.composite_program = self._context.program(
            vertex_shader=blur_vertex, fragment_shader=composite_fragment
        )

    def _create_geometry(self):
        """Create geometry for laser beams and fullscreen quad"""
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

        # Create fullscreen quad for post-processing
        quad_vertices = np.array(
            [
                # Position  # TexCoord
                -1.0,
                -1.0,
                0.0,
                0.0,
                1.0,
                -1.0,
                1.0,
                0.0,
                1.0,
                1.0,
                1.0,
                1.0,
                -1.0,
                1.0,
                0.0,
                1.0,
            ],
            dtype=np.float32,
        )

        quad_indices = np.array([0, 1, 2, 0, 2, 3], dtype=np.uint32)

        quad_vbo = self._context.buffer(quad_vertices.tobytes())
        quad_ibo = self._context.buffer(quad_indices.tobytes())

        self.quad_vao = self._context.vertex_array(
            self.blur_program,
            [(quad_vbo, "2f 2f", "in_position", "in_texcoord")],
            quad_ibo,
        )

    def _create_matrices(self):
        """Create view and projection matrices using camera system"""
        # Use camera system from ConcertStage (never moves)
        view = look_at_matrix(self.camera_eye, self.camera_target, self.camera_up)

        # Projection matrix
        aspect = self.width / self.height
        projection = perspective_matrix(45.0, aspect, 0.1, 100.0)

        return view, projection

    def _get_laser_direction(self, beam: LaserBeam, signal_value: float) -> np.ndarray:
        """Calculate the direction for a specific laser beam based on fan angle and signal"""
        # Base direction is the laser point vector
        base_direction = self.laser_point_vector.copy()

        # Create rotation around the fan axis based on beam's fan angle and signal
        # Signal affects the spread - higher signal = wider fan
        dynamic_fan_angle = beam.fan_angle * (0.5 + signal_value * 0.5)

        # Apply quaternion rotation (using rotation matrix for now)
        rotation_matrix = create_rotation_matrix(
            self.fan_rotation_axis, dynamic_fan_angle
        )

        # Transform the direction
        direction_4d = np.append(
            base_direction, 0.0
        )  # Make it 4D for matrix multiplication
        rotated_direction = (rotation_matrix @ direction_4d)[:3]

        # Normalize
        return rotated_direction / np.linalg.norm(rotated_direction)

    def render(
        self, frame: Frame, scheme: ColorScheme, context: mgl.Context
    ) -> Optional[mgl.Framebuffer]:
        """Render the laser array with bloom effect"""
        if not self.framebuffer or not self.laser_vao:
            return None

        # Get signal value for fanning
        signal_value = frame[self.fan_signal]
        current_time = time.time()

        # Create matrices
        view, projection = self._create_matrices()

        # Render lasers to main framebuffer
        self.framebuffer.use()
        context.clear(0.0, 0.0, 0.0, 0.0)  # Transparent background
        # Depth testing off so thin beams are not lost due to precision
        context.disable(mgl.DEPTH_TEST)
        context.enable(mgl.BLEND)
        context.blend_func = mgl.SRC_ALPHA, mgl.ONE  # Additive blending

        # Render each laser beam
        for beam in self.lasers:
            # Calculate laser direction
            laser_direction = self._get_laser_direction(beam, signal_value)

            # Create model matrix for this laser
            # Translate to laser position and orient along laser direction
            translation = create_translation_matrix(self.laser_position)

            # Create rotation to align Y-axis with laser direction
            # (since our geometry extends along Y-axis)
            up_axis = np.array([0.0, 1.0, 0.0])
            if np.allclose(laser_direction, up_axis):
                rotation = np.eye(4, dtype=np.float32)
            elif np.allclose(laser_direction, -up_axis):
                rotation = create_rotation_matrix(np.array([1.0, 0.0, 0.0]), math.pi)
            else:
                # Create rotation matrix to align up_axis with laser_direction
                axis = np.cross(up_axis, laser_direction)
                axis = axis / np.linalg.norm(axis)
                angle = math.acos(np.clip(np.dot(up_axis, laser_direction), -1.0, 1.0))
                rotation = create_rotation_matrix(axis, angle)

            model = translation @ rotation

            # Set shader uniforms (billboarded in vertex shader)
            self.laser_program["view"].write(view.astype(np.float32).tobytes())
            self.laser_program["projection"].write(
                projection.astype(np.float32).tobytes()
            )
            self.laser_program["camera_position"] = tuple(self.camera_eye)
            self.laser_program["beam_origin"] = tuple(self.laser_position)
            self.laser_program["beam_direction"] = tuple(laser_direction)
            self.laser_program["beam_length"] = float(self.laser_length)
            self.laser_program["beam_half_width"] = float(self.laser_thickness * 0.5)
            # Approximate camera forward from view matrix (third row negative)
            # view matrix has -forward as row 3 (0-based index 2)
            view_arr = view
            np_forward = -view_arr[2, :3]
            np_forward = np_forward / (np.linalg.norm(np_forward) + 1e-6)
            self.laser_program["view_direction"] = tuple(np_forward)
            self.laser_program["laser_color"] = scheme.fg.rgb
            self.laser_program["laser_intensity"] = 5.0 * beam.intensity
            self.laser_program["time"] = current_time

            # Render laser geometry
            self.laser_vao.render(mgl.TRIANGLES)

        context.disable(mgl.DEPTH_TEST)
        context.disable(mgl.BLEND)

        # Apply bloom effect
        self._apply_bloom_effect(context)

        return self.bloom_framebuffer

    def _apply_bloom_effect(self, context: mgl.Context):
        """Apply bloom effect to the rendered lasers"""
        if not (
            self.blur_program
            and self.composite_program
            and self.quad_vao
            and self.blur_framebuffer1
            and self.blur_framebuffer2
        ):
            return

        # Horizontal blur pass
        self.blur_framebuffer1.use()
        context.clear(0.0, 0.0, 0.0, 0.0)
        context.disable(mgl.DEPTH_TEST)
        context.disable(mgl.BLEND)

        self.color_texture.use(0)
        self.blur_program["input_texture"] = 0
        self.blur_program["blur_direction"] = (1.0, 0.0)  # Horizontal
        self.blur_program["blur_radius"] = 2.0

        self.quad_vao.render()

        # Vertical blur pass
        self.blur_framebuffer2.use()
        context.clear(0.0, 0.0, 0.0, 0.0)

        self.blur_texture1.use(0)
        self.blur_program["input_texture"] = 0
        self.blur_program["blur_direction"] = (0.0, 1.0)  # Vertical

        self.quad_vao.render()

        # Composite original + bloom
        self.bloom_framebuffer.use()
        context.clear(0.0, 0.0, 0.0, 0.0)
        context.enable(mgl.BLEND)
        context.blend_func = mgl.SRC_ALPHA, mgl.ONE_MINUS_SRC_ALPHA

        # Create composite VAO
        quad_vertices = np.array(
            [
                -1.0,
                -1.0,
                0.0,
                0.0,
                1.0,
                -1.0,
                1.0,
                0.0,
                1.0,
                1.0,
                1.0,
                1.0,
                -1.0,
                1.0,
                0.0,
                1.0,
            ],
            dtype=np.float32,
        )

        quad_indices = np.array([0, 1, 2, 0, 2, 3], dtype=np.uint32)

        quad_vbo = context.buffer(quad_vertices.tobytes())
        quad_ibo = context.buffer(quad_indices.tobytes())

        composite_quad_vao = context.vertex_array(
            self.composite_program,
            [(quad_vbo, "2f 2f", "in_position", "in_texcoord")],
            quad_ibo,
        )

        self.color_texture.use(0)
        self.blur_texture2.use(1)
        self.composite_program["original_texture"] = 0
        self.composite_program["bloom_texture"] = 1
        self.composite_program["bloom_intensity"] = 1.5

        composite_quad_vao.render()

        # Clean up temporary resources
        composite_quad_vao.release()
        quad_vbo.release()
        quad_ibo.release()

        context.disable(mgl.BLEND)
