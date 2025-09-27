#!/usr/bin/env python3

import time
import math
import random
import numpy as np
import moderngl as mgl
from typing import List, Tuple, Optional
from beartype import beartype

from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode
from parrot.vj.constants import DEFAULT_WIDTH, DEFAULT_HEIGHT
from parrot.vj.utils.math_3d import (
    look_at_matrix,
    perspective_matrix,
    align_to_direction,
    create_translation_matrix,
    spherical_to_cartesian,
)


@beartype
class BeamState:
    """State for a single volumetric beam"""

    def __init__(self, position: np.ndarray, direction: np.ndarray):
        self.position = position.copy()
        self.direction = direction.copy()
        self.target_position = position.copy()
        self.target_direction = direction.copy()
        self.phase_offset = random.uniform(0, 2 * math.pi)

    def update(self, time: float, speed: float, signal: float):
        """Update beam position and direction with smooth movement"""
        # Smooth interpolation towards targets
        lerp_factor = min(1.0, speed * 0.016)  # Assume ~60fps

        self.position += (self.target_position - self.position) * lerp_factor
        self.direction += (self.target_direction - self.direction) * lerp_factor
        self.direction = self.direction / np.linalg.norm(self.direction)

        # Add subtle oscillation based on audio signal
        oscillation = np.array(
            [
                math.sin(time * 2.0 + self.phase_offset) * signal * 0.5,
                0.0,
                math.cos(time * 1.5 + self.phase_offset) * signal * 0.3,
            ]
        )

        self.position += oscillation

    def randomize_target(self):
        """Set new random target position and direction"""
        self.target_position = np.array(
            [
                random.uniform(-6.0, 6.0),
                random.uniform(3.0, 10.0),
                random.uniform(-4.0, 4.0),
            ]
        )

        self.target_direction = np.array(
            [
                random.uniform(-1.0, 1.0),
                random.uniform(-1.0, -0.1),
                random.uniform(-1.0, 1.0),
            ]
        )
        self.target_direction = self.target_direction / np.linalg.norm(
            self.target_direction
        )


@beartype
class VolumetricBeam(BaseInterpretationNode[mgl.Context, None, mgl.Framebuffer]):
    """
    3D volumetric light beam that renders in 3D space with glow and bloom effects.
    Creates concert-style moving light beams that wave around in a hazy atmosphere.
    Renders on top of 2D canvas content using OpenGL 3D primitives.
    """

    def __init__(
        self,
        beam_count: int = 6,
        beam_length: float = 12.0,
        beam_width: float = 0.4,
        beam_intensity: float = 2.5,
        haze_density: float = 0.9,
        movement_speed: float = 1.8,
        color: Tuple[float, float, float] = (1.0, 0.8, 0.6),  # Warm concert lighting
        signal: FrameSignal = FrameSignal.freq_low,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
    ):
        """
        Args:
            beam_count: Number of light beams to render
            beam_length: Length of each beam in 3D units
            beam_width: Width/thickness of beam cone
            beam_intensity: Brightness multiplier for beams
            haze_density: Density of atmospheric haze for volumetric effect
            movement_speed: Speed of beam movement/rotation
            color: RGB color of the beams (0.0-1.0)
            signal: Audio signal controlling beam movement
            width: Render target width
            height: Render target height
        """
        super().__init__([])
        self.beam_count = beam_count
        self.beam_length = beam_length
        self.beam_width = beam_width
        self.beam_intensity = beam_intensity
        self.haze_density = haze_density
        self.movement_speed = movement_speed
        self.color = color
        self.signal = signal
        self.width = width
        self.height = height

        # 3D rendering state
        self.beams: List[BeamState] = []
        self.start_time = time.time()

        # OpenGL resources
        self.framebuffer: Optional[mgl.Framebuffer] = None
        self.color_texture: Optional[mgl.Texture] = None
        self.depth_texture: Optional[mgl.Texture] = None
        self.bloom_framebuffer: Optional[mgl.Framebuffer] = None
        self.bloom_texture: Optional[mgl.Texture] = None

        # Shaders and geometry
        self.beam_program: Optional[mgl.Program] = None
        self.haze_program: Optional[mgl.Program] = None
        self.bloom_program: Optional[mgl.Program] = None
        self.beam_vao: Optional[mgl.VertexArray] = None
        self.quad_vao: Optional[mgl.VertexArray] = None

        self._context: Optional[mgl.Context] = None

    def enter(self, context: mgl.Context):
        """Initialize 3D volumetric beam resources"""
        self._context = context
        self._setup_beams()
        self._setup_gl_resources()

    def exit(self):
        """Clean up 3D beam resources"""
        resources = [
            self.framebuffer,
            self.color_texture,
            self.depth_texture,
            self.bloom_framebuffer,
            self.bloom_texture,
            self.beam_program,
            self.haze_program,
            self.bloom_program,
            self.beam_vao,
            self.quad_vao,
        ]

        for resource in resources:
            if resource:
                resource.release()

        self._context = None

    def generate(self, vibe: Vibe):
        """Generate new beam configurations based on vibe"""
        # Randomly pick a signal from available Frame signals
        available_signals = [
            FrameSignal.freq_all,
            FrameSignal.freq_high,
            FrameSignal.freq_low,
            FrameSignal.sustained_low,
            FrameSignal.sustained_high,
            FrameSignal.strobe,
            FrameSignal.big_blinder,
            FrameSignal.small_blinder,
            FrameSignal.pulse,
            FrameSignal.dampen,
        ]
        self.signal = random.choice(available_signals)

        # Adjust beam intensity based on mode
        if vibe.mode == Mode.rave:
            self.beam_intensity = 3.5  # High energy, very visible
            self.haze_density = 1.0
        elif vibe.mode == Mode.gentle:
            self.beam_intensity = 2.0  # Increased from 0.8 to be visible
            self.haze_density = 0.8  # Increased from 0.6 to be visible
        elif vibe.mode == Mode.blackout:
            self.beam_intensity = 0.0
            self.haze_density = 0.0

        # Randomize beam positions and orientations
        for beam in self.beams:
            if random.random() < 0.1:  # 10% chance to randomize each beam
                beam.randomize_target()

    def _setup_beams(self):
        """Initialize beam state objects"""
        self.beams = []
        for i in range(self.beam_count):
            beam = BeamState(
                position=np.array(
                    [
                        random.uniform(-5.0, 5.0),  # X
                        random.uniform(2.0, 8.0),  # Y (above ground)
                        random.uniform(-3.0, 3.0),  # Z
                    ]
                ),
                direction=np.array(
                    [
                        random.uniform(-1.0, 1.0),
                        random.uniform(-0.8, -0.2),  # Point generally downward
                        random.uniform(-1.0, 1.0),
                    ]
                ),
            )
            beam.direction = beam.direction / np.linalg.norm(beam.direction)
            self.beams.append(beam)

    def print_self(self) -> str:
        """Return class name with current signal in brackets"""
        return f"{self.__class__.__name__} [{self.signal.name}]"

    def _setup_gl_resources(self):
        """Setup OpenGL resources for 3D beam rendering"""
        if not self._context:
            return

        # Create framebuffers for 3D rendering
        self.color_texture = self._context.texture((self.width, self.height), 4)  # RGBA
        self.depth_texture = self._context.depth_texture((self.width, self.height))
        self.framebuffer = self._context.framebuffer(
            color_attachments=[self.color_texture], depth_attachment=self.depth_texture
        )

        # Bloom framebuffer (half resolution for performance)
        bloom_width, bloom_height = self.width // 2, self.height // 2
        self.bloom_texture = self._context.texture((bloom_width, bloom_height), 4)
        self.bloom_framebuffer = self._context.framebuffer(
            color_attachments=[self.bloom_texture]
        )

        # Create shader programs
        self._create_shaders()

        # Create geometry
        self._create_beam_geometry()
        self._create_quad_geometry()

    def _create_shaders(self):
        """Create shader programs for beam rendering"""
        # Volumetric beam vertex shader
        beam_vertex = """
        #version 330 core
        in vec3 in_position;
        in vec3 in_normal;
        in float in_distance;
        
        uniform mat4 mvp_matrix;
        uniform mat4 model_matrix;
        uniform vec3 beam_origin;
        uniform float beam_length;
        
        out vec3 world_pos;
        out vec3 normal;
        out float distance_along_beam;
        out float distance_from_origin;
        
        void main() {
            vec4 world_position = model_matrix * vec4(in_position, 1.0);
            world_pos = world_position.xyz;
            normal = normalize((model_matrix * vec4(in_normal, 0.0)).xyz);
            distance_along_beam = in_distance;
            distance_from_origin = length(world_pos - beam_origin);
            
            gl_Position = mvp_matrix * world_position;
        }
        """

        # Volumetric beam fragment shader
        beam_fragment = """
        #version 330 core
        in vec3 world_pos;
        in vec3 normal;
        in float distance_along_beam;
        in float distance_from_origin;
        
        uniform vec3 beam_color;
        uniform float beam_intensity;
        uniform float haze_density;
        uniform vec3 camera_pos;
        uniform vec3 beam_origin;
        uniform float beam_length;
        
        out vec4 color;
        
        void main() {
            // Distance-based attenuation
            float distance_falloff = 1.0 / (1.0 + distance_from_origin * 0.1);
            
            // Beam cone falloff (brighter in center)
            float cone_falloff = 1.0 - smoothstep(0.0, 1.0, distance_along_beam);
            
            // Volumetric scattering effect
            vec3 view_dir = normalize(camera_pos - world_pos);
            float scattering = pow(max(0.0, dot(view_dir, -normalize(world_pos))), 2.0);
            
            // Combine effects
            float intensity = beam_intensity * distance_falloff * cone_falloff * 
                            (0.3 + 0.7 * scattering) * haze_density;
            
            color = vec4(beam_color * intensity, intensity * 0.8);
        }
        """

        # Bloom post-processing shader
        bloom_vertex = """
        #version 330 core
        in vec2 in_position;
        in vec2 in_texcoord;
        out vec2 uv;
        
        void main() {
            gl_Position = vec4(in_position, 0.0, 1.0);
            uv = in_texcoord;
        }
        """

        bloom_fragment = """
        #version 330 core
        in vec2 uv;
        out vec4 color;
        uniform sampler2D input_texture;
        uniform float bloom_threshold;
        uniform float bloom_intensity;
        
        void main() {
            vec4 input_color = texture(input_texture, uv);
            
            // Extract bright areas
            float brightness = dot(input_color.rgb, vec3(0.299, 0.587, 0.114));
            vec3 bloom_color = vec3(0.0);
            
            if (brightness > bloom_threshold) {
                bloom_color = input_color.rgb * bloom_intensity;
            }
            
            // Simple box blur for bloom effect
            vec2 tex_offset = 1.0 / textureSize(input_texture, 0);
            for (int x = -2; x <= 2; x++) {
                for (int y = -2; y <= 2; y++) {
                    vec2 offset = vec2(float(x), float(y)) * tex_offset;
                    vec4 sample_color = texture(input_texture, uv + offset);
                    float sample_brightness = dot(sample_color.rgb, vec3(0.299, 0.587, 0.114));
                    if (sample_brightness > bloom_threshold) {
                        bloom_color += sample_color.rgb * 0.04; // 1/25 for 5x5 kernel
                    }
                }
            }
            
            color = vec4(input_color.rgb + bloom_color, input_color.a);
        }
        """

        self.beam_program = self._context.program(
            vertex_shader=beam_vertex, fragment_shader=beam_fragment
        )

        self.bloom_program = self._context.program(
            vertex_shader=bloom_vertex, fragment_shader=bloom_fragment
        )

    def _create_beam_geometry(self):
        """Create 3D geometry for volumetric beam cones"""
        # Create a cone mesh for each beam
        vertices = []
        indices = []

        # Cone parameters
        segments = 16

        # Apex of cone (beam origin)
        vertices.extend([0.0, 0.0, 0.0, 0.0, 1.0, 0.0, 0.0])  # pos, normal, distance

        # Base circle vertices
        for i in range(segments):
            angle = 2.0 * math.pi * i / segments
            x = math.cos(angle) * self.beam_width
            z = math.sin(angle) * self.beam_width
            y = -self.beam_length

            # Normal pointing outward from cone surface
            normal_x = math.cos(angle)
            normal_y = 0.3  # Slight upward component
            normal_z = math.sin(angle)
            normal_len = math.sqrt(
                normal_x * normal_x + normal_y * normal_y + normal_z * normal_z
            )

            vertices.extend(
                [
                    x,
                    y,
                    z,
                    normal_x / normal_len,
                    normal_y / normal_len,
                    normal_z / normal_len,
                    1.0,  # Distance from center (for cone falloff)
                ]
            )

        # Create triangular faces
        for i in range(segments):
            next_i = (i + 1) % segments
            # Triangle from apex to base edge
            indices.extend([0, i + 1, next_i + 1])

        # Base cap (optional, for closed cone)
        base_center_idx = len(vertices) // 7
        vertices.extend([0.0, -self.beam_length, 0.0, 0.0, -1.0, 0.0, 1.0])

        for i in range(segments):
            next_i = (i + 1) % segments
            indices.extend([base_center_idx, next_i + 1, i + 1])

        # Convert to numpy arrays
        vertices_array = np.array(vertices, dtype=np.float32)
        indices_array = np.array(indices, dtype=np.uint32)

        # Create VAO
        vbo = self._context.buffer(vertices_array.tobytes())
        ibo = self._context.buffer(indices_array.tobytes())

        self.beam_vao = self._context.vertex_array(
            self.beam_program,
            [(vbo, "3f 3f 1f", "in_position", "in_normal", "in_distance")],
            ibo,
        )

    def _create_quad_geometry(self):
        """Create fullscreen quad for post-processing"""
        vertices = np.array(
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
                -1.0,
                1.0,
                0.0,
                1.0,
                1.0,
                1.0,
                1.0,
                1.0,
            ],
            dtype=np.float32,
        )

        vbo = self._context.buffer(vertices.tobytes())
        self.quad_vao = self._context.vertex_array(
            self.bloom_program, [(vbo, "2f 2f", "in_position", "in_texcoord")]
        )

    def _create_matrices(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Create view, projection, and model matrices"""
        # Camera setup (looking down at the scene)
        camera_pos = np.array([0.0, 12.0, 8.0])
        target = np.array([0.0, 0.0, 0.0])
        up = np.array([0.0, 1.0, 0.0])

        # View matrix
        view = look_at_matrix(camera_pos, target, up)

        # Projection matrix
        aspect = self.width / self.height
        projection = perspective_matrix(45.0, aspect, 0.1, 100.0)

        # Model matrix (identity for now)
        model = np.eye(4, dtype=np.float32)

        return view, projection, model, camera_pos

    def render(
        self, frame: Frame, scheme: ColorScheme, context: mgl.Context
    ) -> Optional[mgl.Framebuffer]:
        """Render 3D volumetric beams with bloom effect"""
        if not self.framebuffer or not self.beam_vao:
            # Create a minimal framebuffer if not set up
            if not self.framebuffer:
                try:
                    color_texture = context.texture((self.width, self.height), 4)
                    self.framebuffer = context.framebuffer(
                        color_attachments=[color_texture]
                    )
                    self.framebuffer.use()
                    context.clear(0.0, 0.0, 0.0, 0.0)
                except:
                    # If GL setup fails, create a mock framebuffer for testing
                    pass
            return self.framebuffer

        # Update beam animations
        self._update_beams(frame)

        # Create matrices
        view, projection, model, camera_pos = self._create_matrices()
        mvp = projection @ view @ model

        # Render beams to main framebuffer
        self.framebuffer.use()
        context.clear(0.0, 0.0, 0.0, 0.0)  # Transparent background
        context.enable(mgl.DEPTH_TEST)
        context.enable(mgl.BLEND)
        context.blend_func = mgl.SRC_ALPHA, mgl.ONE  # Additive blending for glow

        # Get signal value for intensity modulation
        signal_value = frame[self.signal]
        dynamic_intensity = self.beam_intensity * (0.5 + signal_value * 0.5)

        # Render each beam
        for beam in self.beams:
            # Create model matrix for this beam
            beam_model = self._create_beam_transform(beam)
            beam_mvp = projection @ view @ beam_model

            # Set uniforms (only set uniforms that exist in the shader)
            self.beam_program["mvp_matrix"].write(beam_mvp.astype(np.float32).tobytes())
            self.beam_program["model_matrix"].write(
                beam_model.astype(np.float32).tobytes()
            )

            # Set shader uniforms
            try:
                self.beam_program["beam_origin"] = tuple(beam.position)
                self.beam_program["beam_length"] = self.beam_length
                self.beam_program["beam_color"] = self.color
                self.beam_program["beam_intensity"] = dynamic_intensity
                self.beam_program["haze_density"] = self.haze_density
                self.beam_program["camera_pos"] = tuple(camera_pos)
            except KeyError as e:
                # If a uniform doesn't exist, that's okay - just skip it
                pass

            # Render beam geometry
            self.beam_vao.render()

        # Apply bloom post-processing
        self._apply_bloom(context)

        context.disable(mgl.DEPTH_TEST)
        context.disable(mgl.BLEND)

        return self.framebuffer

    def _update_beams(self, frame: Frame):
        """Update beam positions and orientations"""
        current_time = time.time() - self.start_time
        signal_value = frame[self.signal]

        for i, beam in enumerate(self.beams):
            # Smooth movement towards target
            beam.update(current_time, self.movement_speed, signal_value)

    def _create_beam_transform(self, beam: BeamState) -> np.ndarray:
        """Create transformation matrix for a beam"""
        # Create rotation matrix to align beam with direction
        rotation = align_to_direction(beam.direction)

        # Create translation matrix
        translation = create_translation_matrix(beam.position)

        # Combine translation and rotation
        transform = translation @ rotation

        return transform

    def _apply_bloom(self, context: mgl.Context):
        """Apply bloom post-processing effect"""
        if not self.bloom_framebuffer or not self.quad_vao:
            return

        # Render bloom effect to bloom framebuffer
        self.bloom_framebuffer.use()
        context.clear(0.0, 0.0, 0.0, 0.0)

        self.color_texture.use(0)
        self.bloom_program["input_texture"] = 0
        self.bloom_program["bloom_threshold"] = 0.5
        self.bloom_program["bloom_intensity"] = 1.5

        self.quad_vao.render(mgl.TRIANGLE_STRIP)

        # Composite bloom back onto main framebuffer
        self.framebuffer.use()
        context.enable(mgl.BLEND)
        context.blend_func = mgl.ONE, mgl.ONE  # Additive

        self.bloom_texture.use(0)
        self.quad_vao.render(mgl.TRIANGLE_STRIP)

        context.disable(mgl.BLEND)
