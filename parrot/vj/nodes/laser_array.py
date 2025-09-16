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
    create_rotation_matrix,
    spherical_to_cartesian,
)


@beartype
class LaserBeamState:
    """State for a single laser beam in the array"""

    def __init__(self, position: np.ndarray, direction: np.ndarray, beam_id: int):
        self.position = position.copy()
        self.direction = direction.copy()
        self.target_position = position.copy()
        self.target_direction = direction.copy()
        self.beam_id = beam_id
        self.phase_offset = random.uniform(0, 2 * math.pi)
        self.scan_phase = random.uniform(0, 2 * math.pi)
        self.intensity = 1.0
        self.target_intensity = 1.0

    def update(self, time: float, speed: float, signal: float, fan_angle: float):
        """Update laser beam position and direction with scanning motion"""
        # Smooth interpolation towards targets
        lerp_factor = min(1.0, speed * 0.016)  # Assume ~60fps

        self.position += (self.target_position - self.position) * lerp_factor
        self.direction += (self.target_direction - self.direction) * lerp_factor
        self.direction = self.direction / np.linalg.norm(self.direction)

        # Laser scanning motion (side-to-side sweep)
        scan_speed = 3.0 + signal * 2.0  # Faster scanning with higher signal
        self.scan_phase += scan_speed * 0.016

        # Create scanning motion by rotating around Y-axis
        scan_amplitude = fan_angle * (0.5 + signal * 0.5)  # Signal affects fan width
        scan_offset = math.sin(self.scan_phase + self.phase_offset) * scan_amplitude

        # Apply scanning rotation to direction
        scan_rotation = create_rotation_matrix(np.array([0.0, 1.0, 0.0]), scan_offset)
        base_direction = self.target_direction.copy()
        rotated_direction = (scan_rotation @ np.append(base_direction, 1.0))[:3]
        self.direction = rotated_direction / np.linalg.norm(rotated_direction)

        # Intensity modulation
        self.intensity += (self.target_intensity - self.intensity) * lerp_factor * 2.0

    def randomize_target(self, array_center: np.ndarray, spread_radius: float):
        """Set new random target position within array bounds"""
        # Keep lasers in a circular array formation
        angle = random.uniform(0, 2 * math.pi)
        radius = random.uniform(0.5, spread_radius)

        offset = np.array(
            [
                math.cos(angle) * radius,
                random.uniform(-0.5, 0.5),  # Small vertical variation
                math.sin(angle) * radius,
            ]
        )

        self.target_position = array_center + offset

        # Point generally forward and slightly downward
        self.target_direction = np.array(
            [
                random.uniform(-0.3, 0.3),
                random.uniform(-0.8, -0.2),
                random.uniform(-1.0, -0.5),
            ]
        )
        self.target_direction = self.target_direction / np.linalg.norm(
            self.target_direction
        )

        # Randomize intensity
        self.target_intensity = random.uniform(0.7, 1.0)


@beartype
class LaserArray(BaseInterpretationNode[mgl.Context, None, mgl.Framebuffer]):
    """
    3D laser array that creates multiple thin laser beams that fan out and narrow.
    Creates concert/club-style laser shows with scanning patterns and strobing effects.
    """

    def __init__(
        self,
        laser_count: int = 8,
        array_radius: float = 2.0,
        laser_length: float = 20.0,
        laser_width: float = 0.02,  # Very thin for laser effect
        fan_angle: float = math.pi / 3,  # 60 degrees fan spread
        scan_speed: float = 2.0,
        strobe_frequency: float = 0.0,  # 0 = no strobe, >0 = strobe Hz
        laser_intensity: float = 2.0,  # Very bright for laser effect
        color: Tuple[float, float, float] = (0.0, 1.0, 0.0),  # Green laser
        signal: FrameSignal = FrameSignal.freq_high,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
    ):
        """
        Args:
            laser_count: Number of laser beams in the array
            array_radius: Radius of the laser array formation
            laser_length: Length of each laser beam
            laser_width: Width/thickness of laser beams (very thin)
            fan_angle: Maximum angle for laser fan spread (radians)
            scan_speed: Speed of laser scanning motion
            strobe_frequency: Strobe frequency in Hz (0 = no strobe)
            laser_intensity: Brightness multiplier for lasers
            color: RGB color of the lasers
            signal: Audio signal controlling laser movement
            width: Render target width
            height: Render target height
        """
        super().__init__([])
        self.laser_count = laser_count
        self.array_radius = array_radius
        self.laser_length = laser_length
        self.laser_width = laser_width
        self.fan_angle = fan_angle
        self.scan_speed = scan_speed
        self.strobe_frequency = strobe_frequency
        self.laser_intensity = laser_intensity
        self.color = color
        self.signal = signal
        self.width = width
        self.height = height

        # 3D rendering state
        self.lasers: List[LaserBeamState] = []
        self.array_center = np.array([0.0, 5.0, 0.0])
        self.start_time = time.time()
        self.last_strobe_time = 0.0

        # OpenGL resources
        self.framebuffer: Optional[mgl.Framebuffer] = None
        self.color_texture: Optional[mgl.Texture] = None
        self.depth_texture: Optional[mgl.Texture] = None

        # Shaders and geometry
        self.laser_program: Optional[mgl.Program] = None
        self.laser_vao: Optional[mgl.VertexArray] = None

        self._context: Optional[mgl.Context] = None

    def enter(self, context: mgl.Context):
        """Initialize 3D laser array resources"""
        self._context = context
        self._setup_lasers()
        self._setup_gl_resources()

    def exit(self):
        """Clean up 3D laser resources"""
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
        """Generate new laser configurations based on vibe"""
        # Adjust laser behavior based on mode
        if vibe.mode == Mode.rave:
            # High energy: fan out lasers and add strobe
            self.fan_out_beams()
            self.set_strobe_frequency(8.0)
        elif vibe.mode == Mode.gentle:
            # Calm: narrow beams and no strobe
            self.narrow_beams()
            self.set_strobe_frequency(0.0)
        elif vibe.mode == Mode.blackout:
            # Blackout: minimal lighting
            self.set_strobe_frequency(0.0)
            self.narrow_beams()

        # Randomize laser positions and orientations
        for laser in self.lasers:
            if random.random() < 0.15:  # 15% chance to randomize each laser
                laser.randomize_target(self.array_center, self.array_radius)

    def _setup_lasers(self):
        """Initialize laser beam state objects in array formation"""
        self.lasers = []
        for i in range(self.laser_count):
            # Arrange lasers in a circular array
            angle = (2 * math.pi * i) / self.laser_count
            radius = self.array_radius * (0.7 + random.uniform(0, 0.3))

            position = self.array_center + np.array(
                [
                    math.cos(angle) * radius,
                    random.uniform(-0.5, 0.5),  # Small height variation
                    math.sin(angle) * radius,
                ]
            )

            # Point lasers generally forward and slightly down
            direction = np.array(
                [
                    random.uniform(-0.2, 0.2),
                    random.uniform(-0.7, -0.3),
                    random.uniform(-1.0, -0.6),
                ]
            )
            direction = direction / np.linalg.norm(direction)

            laser = LaserBeamState(position, direction, i)
            self.lasers.append(laser)

    def _setup_gl_resources(self):
        """Setup OpenGL resources for 3D laser rendering"""
        if not self._context:
            return

        # Create framebuffers for 3D rendering
        self.color_texture = self._context.texture((self.width, self.height), 4)
        self.depth_texture = self._context.depth_texture((self.width, self.height))
        self.framebuffer = self._context.framebuffer(
            color_attachments=[self.color_texture], depth_attachment=self.depth_texture
        )

        # Create shader programs
        self._create_shaders()

        # Create geometry
        self._create_laser_geometry()

    def _create_shaders(self):
        """Create shader programs for laser rendering"""
        # Laser vertex shader
        laser_vertex = """
        #version 330 core
        in vec3 in_position;
        in float in_distance;
        
        uniform mat4 mvp_matrix;
        uniform mat4 model_matrix;
        uniform vec3 laser_origin;
        uniform float laser_length;
        
        out vec3 world_pos;
        out float distance_along_laser;
        out float distance_from_origin;
        
        void main() {
            vec4 world_position = model_matrix * vec4(in_position, 1.0);
            world_pos = world_position.xyz;
            distance_along_laser = in_distance;
            distance_from_origin = length(world_pos - laser_origin);
            
            gl_Position = mvp_matrix * world_position;
        }
        """

        # Laser fragment shader
        laser_fragment = """
        #version 330 core
        in vec3 world_pos;
        in float distance_along_laser;
        in float distance_from_origin;
        
        uniform vec3 laser_color;
        uniform float laser_intensity;
        uniform float strobe_factor;
        uniform vec3 camera_pos;
        uniform float time;
        
        out vec4 color;
        
        void main() {
            // Distance-based attenuation (less than volumetric beams)
            float distance_falloff = 1.0 / (1.0 + distance_from_origin * 0.05);
            
            // Laser beam core intensity (very bright in center)
            float core_intensity = 1.0 - smoothstep(0.0, 0.1, distance_along_laser);
            
            // Add laser sparkle/shimmer effect
            float shimmer = 0.8 + 0.2 * sin(time * 20.0 + world_pos.x * 10.0 + world_pos.z * 10.0);
            
            // Combine effects
            float intensity = laser_intensity * distance_falloff * core_intensity * 
                            shimmer * strobe_factor;
            
            // Laser beams are very saturated and bright
            color = vec4(laser_color * intensity, intensity);
        }
        """

        self.laser_program = self._context.program(
            vertex_shader=laser_vertex, fragment_shader=laser_fragment
        )

    def _create_laser_geometry(self):
        """Create 3D geometry for thin laser beams"""
        # Create a very thin cylinder/line for each laser
        vertices = []
        indices = []

        # Simple line geometry for laser beam
        segments = 4  # Minimal geometry for thin laser

        # Start point (laser origin)
        vertices.extend([0.0, 0.0, 0.0, 0.0])  # pos, distance

        # End point (laser terminus)
        vertices.extend([0.0, -self.laser_length, 0.0, 1.0])  # pos, distance

        # Create additional points for slight width
        for i in range(segments):
            angle = 2.0 * math.pi * i / segments
            x = math.cos(angle) * self.laser_width
            z = math.sin(angle) * self.laser_width

            # Points along the laser beam
            vertices.extend([x, 0.0, z, 0.0])  # Start
            vertices.extend([x, -self.laser_length, z, 1.0])  # End

        # Create line indices for laser beam
        # Main beam line
        indices.extend([0, 1])

        # Side lines for minimal width
        for i in range(segments):
            start_idx = 2 + i * 2
            end_idx = start_idx + 1
            indices.extend([start_idx, end_idx])

            # Connect to main beam
            indices.extend([0, start_idx])
            indices.extend([1, end_idx])

        # Convert to numpy arrays
        vertices_array = np.array(vertices, dtype=np.float32)
        indices_array = np.array(indices, dtype=np.uint32)

        # Create VAO
        vbo = self._context.buffer(vertices_array.tobytes())
        ibo = self._context.buffer(indices_array.tobytes())

        self.laser_vao = self._context.vertex_array(
            self.laser_program,
            [(vbo, "3f 1f", "in_position", "in_distance")],
            ibo,
        )

    def _create_matrices(self) -> Tuple[np.ndarray, np.ndarray, np.ndarray, np.ndarray]:
        """Create view, projection, and model matrices"""
        # Camera setup (looking at the laser array)
        camera_pos = np.array([0.0, 8.0, 12.0])
        target = self.array_center
        up = np.array([0.0, 1.0, 0.0])

        # View matrix
        view = look_at_matrix(camera_pos, target, up)

        # Projection matrix
        aspect = self.width / self.height
        projection = perspective_matrix(45.0, aspect, 0.1, 100.0)

        # Model matrix (identity for now)
        model = np.eye(4, dtype=np.float32)

        return view, projection, model, camera_pos

    def _calculate_strobe_factor(self, current_time: float) -> float:
        """Calculate strobe intensity factor"""
        if self.strobe_frequency <= 0:
            return 1.0

        # Strobe on/off pattern
        strobe_period = 1.0 / self.strobe_frequency
        phase = (current_time % strobe_period) / strobe_period

        # Sharp on/off strobe
        return 1.0 if phase < 0.5 else 0.0

    def render(
        self, frame: Frame, scheme: ColorScheme, context: mgl.Context
    ) -> Optional[mgl.Framebuffer]:
        """Render 3D laser array"""
        if not self.framebuffer or not self.laser_vao:
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

        # Update laser animations
        self._update_lasers(frame)

        # Create matrices
        view, projection, model, camera_pos = self._create_matrices()

        # Render lasers to main framebuffer
        self.framebuffer.use()
        context.clear(0.0, 0.0, 0.0, 0.0)  # Transparent background
        context.enable(mgl.DEPTH_TEST)
        context.enable(mgl.BLEND)
        context.blend_func = mgl.SRC_ALPHA, mgl.ONE  # Additive blending for laser glow

        # Get signal value and time for effects
        signal_value = frame[self.signal]
        current_time = time.time() - self.start_time
        strobe_factor = self._calculate_strobe_factor(current_time)

        # Dynamic intensity modulation
        dynamic_intensity = self.laser_intensity * (0.7 + signal_value * 0.3)

        # Render each laser
        for laser in self.lasers:
            # Create model matrix for this laser
            laser_model = self._create_laser_transform(laser)
            laser_mvp = projection @ view @ laser_model

            # Set uniforms (only set uniforms that exist in the shader)
            self.laser_program["mvp_matrix"].write(
                laser_mvp.astype(np.float32).tobytes()
            )
            self.laser_program["model_matrix"].write(
                laser_model.astype(np.float32).tobytes()
            )

            # Only set uniforms that are actually used in the shader
            if "laser_origin" in self.laser_program:
                self.laser_program["laser_origin"] = tuple(laser.position)
            if "laser_length" in self.laser_program:
                self.laser_program["laser_length"] = self.laser_length
            if "laser_color" in self.laser_program:
                self.laser_program["laser_color"] = self.color
            if "laser_intensity" in self.laser_program:
                self.laser_program["laser_intensity"] = (
                    dynamic_intensity * laser.intensity
                )
            if "strobe_factor" in self.laser_program:
                self.laser_program["strobe_factor"] = strobe_factor
            if "camera_pos" in self.laser_program:
                self.laser_program["camera_pos"] = tuple(camera_pos)
            if "time" in self.laser_program:
                self.laser_program["time"] = current_time

            # Render laser geometry as lines
            self.laser_vao.render(mgl.LINES)

        context.disable(mgl.DEPTH_TEST)
        context.disable(mgl.BLEND)

        return self.framebuffer

    def _update_lasers(self, frame: Frame):
        """Update laser positions and orientations"""
        current_time = time.time() - self.start_time
        signal_value = frame[self.signal]

        # Update fan angle based on signal
        dynamic_fan_angle = self.fan_angle * (0.5 + signal_value * 0.5)

        for laser in self.lasers:
            # Smooth movement and scanning
            laser.update(current_time, self.scan_speed, signal_value, dynamic_fan_angle)

    def _create_laser_transform(self, laser: LaserBeamState) -> np.ndarray:
        """Create transformation matrix for a laser beam"""
        # Create rotation matrix to align laser with direction
        rotation = align_to_direction(laser.direction)

        # Create translation matrix
        translation = create_translation_matrix(laser.position)

        # Combine translation and rotation
        transform = translation @ rotation

        return transform

    def set_fan_angle(self, angle: float):
        """Dynamically adjust the fan angle"""
        self.fan_angle = max(0.0, min(math.pi, angle))

    def set_strobe_frequency(self, frequency: float):
        """Dynamically adjust the strobe frequency"""
        if frequency < 0.0:
            raise ValueError(f"Strobe frequency must be non-negative, got {frequency}")
        self.strobe_frequency = frequency

    def narrow_beams(self):
        """Narrow all laser beams to point forward"""
        for laser in self.lasers:
            laser.target_direction = np.array([0.0, -0.8, -0.6])
            laser.target_direction = laser.target_direction / np.linalg.norm(
                laser.target_direction
            )

    def fan_out_beams(self):
        """Fan out laser beams in different directions"""
        for i, laser in enumerate(self.lasers):
            # Spread beams in a fan pattern
            angle = (2 * math.pi * i) / len(self.lasers)
            spread = self.fan_angle * 0.5

            direction = np.array(
                [
                    math.sin(angle) * spread,
                    -0.7,
                    -0.7 + math.cos(angle) * spread,
                ]
            )
            laser.target_direction = direction / np.linalg.norm(direction)
