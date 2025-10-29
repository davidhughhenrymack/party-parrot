#!/usr/bin/env python3

from beartype import beartype
from typing import Optional, Any
import math

from parrot.fixtures.moving_head import MovingHead
from parrot.vj.renderers.base import FixtureRenderer, quaternion_from_axis_angle, quaternion_multiply
from parrot.director.frame import Frame
import numpy as np


@beartype
class MovingHeadRenderer(FixtureRenderer):
    """3D Renderer for moving head fixtures - gray body + sphere + beam (TODO)"""

    def __init__(self, fixture: MovingHead, room_renderer: Optional[Any] = None):
        super().__init__(fixture, room_renderer)

    def _get_default_size(self) -> tuple[float, float]:
        return (40.0, 40.0)

    def get_angles(self) -> tuple[float, float]:
        """Return pan and tilt angles in radians"""
        pan_rad = math.radians(self.fixture.get_pan_angle())
        tilt_rad = math.radians(self.fixture.get_tilt_angle())
        return pan_rad, tilt_rad

    def render_opaque(self, context, canvas_size: tuple[float, float], frame: Frame):
        """Render only the opaque Blinn-Phong parts (fixed base + moving body)"""
        if self.room_renderer is None:
            return

        # Get 3D position (center of fixture)
        position_3d = self.get_3d_position(canvas_size)

        # Render with local transforms
        with self.room_renderer.local_position(position_3d):
            with self.room_renderer.local_rotation(self.orientation):
                body_size = self.cube_size * 0.4
                body_color = (0.3, 0.3, 0.3)

                # === FIXED BASE ===
                # Base is shorter (less tall) and wider, sits on floor
                base_height = body_size * 0.3  # Much shorter base
                base_width = body_size * 1.2   # Wider than tall
                base_depth = body_size * 0.8    # Slightly shorter in depth
                
                # Base sits on floor (y=0 to y=base_height)
                self.room_renderer.render_rectangular_box(
                    0.0, base_height / 2, 0.0, body_color, base_width, base_height, base_depth
                )

                # === MOVING BODY ===
                # Moving body (yoke + head) rotates with pan/tilt
                pan_rad, tilt_rad = self.get_angles()
                pan_rad *= 0.5
                tilt_rad *= 0.5
                pan_rad += math.pi

                # Create quaternions for pan (around Y axis) and tilt (around X axis)
                y_axis = np.array([0.0, 1.0, 0.0], dtype=np.float32)
                x_axis = np.array([1.0, 0.0, 0.0], dtype=np.float32)
                
                # Pan rotates around Y axis (horizontal rotation)
                pan_quat = quaternion_from_axis_angle(y_axis, pan_rad)
                
                # Tilt rotates around X axis (vertical rotation)
                tilt_quat = quaternion_from_axis_angle(x_axis, tilt_rad)
                
                # Compose rotations: first pan, then tilt
                moving_body_rotation = quaternion_multiply(tilt_quat, pan_quat)

                # Render moving body (yoke + head) above the base
                with self.room_renderer.local_rotation(moving_body_rotation):
                    # Moving body: shorter height, longer depth, square front face
                    moving_body_height = body_size * 0.5  # Shorter height
                    moving_body_width = body_size * 0.5   # Square front face (width = height)
                    moving_body_depth = body_size * 1.2   # Longer depth
                    
                    # Position moving body higher on top of base
                    moving_body_y = base_height + moving_body_height / 2 + body_size * 0.3
                    
                    self.room_renderer.render_rectangular_box(
                        0.0, moving_body_y, 0.0, body_color, 
                        moving_body_width, moving_body_height, moving_body_depth
                    )

        # Render DMX address
        self.render_dmx_address(canvas_size)

    def render_emissive(self, context, canvas_size: tuple[float, float], frame: Frame):
        """Render only the emissive parts (bulb and beam)"""
        if self.room_renderer is None:
            return

        # Get 3D position (center of fixture)
        position_3d = self.get_3d_position(canvas_size)

        # Render with local transforms
        with self.room_renderer.local_position(position_3d):
            with self.room_renderer.local_rotation(self.orientation):
                body_size = self.cube_size * 0.4
                base_height = body_size * 0.3  # Match base height from render_opaque
                moving_body_height = body_size * 0.5  # Match moving body height from render_opaque
                
                # Bulb and beam are attached to moving body
                bulb_radius = body_size * 0.3  # Increased size for visibility
                bulb_distance = body_size * 0.7
                bulb_color = self.get_color()
                dimmer = self.get_effective_dimmer(frame)

                # Calculate beam direction based on pan/tilt
                pan_rad, tilt_rad = self.get_angles()
                pan_rad *= 0.5
                tilt_rad *= 0.5
                pan_rad += math.pi

                # Calculate beam direction vector
                cos_tilt = math.cos(tilt_rad)
                sin_tilt = math.sin(tilt_rad)
                cos_pan = math.cos(pan_rad)
                sin_pan = math.sin(pan_rad)

                beam_dir_x = sin_pan * cos_tilt
                beam_dir_y = -sin_tilt
                beam_dir_z = cos_pan * cos_tilt
                beam_direction = (beam_dir_x, beam_dir_y, beam_dir_z)

                # Create quaternions for pan (around Y axis) and tilt (around X axis)
                y_axis = np.array([0.0, 1.0, 0.0], dtype=np.float32)
                x_axis = np.array([1.0, 0.0, 0.0], dtype=np.float32)
                
                # Pan rotates around Y axis (horizontal rotation)
                pan_quat = quaternion_from_axis_angle(y_axis, pan_rad)
                
                # Tilt rotates around X axis (vertical rotation)
                tilt_quat = quaternion_from_axis_angle(x_axis, tilt_rad)
                
                # Compose rotations: first pan, then tilt
                moving_body_rotation = quaternion_multiply(tilt_quat, pan_quat)

                # Render bulb and beam attached to moving body
                with self.room_renderer.local_rotation(moving_body_rotation):
                    # Bulb position relative to moving body (lower, at front face of moving body)
                    # Beam comes from the front face of the moving body
                    bulb_y = base_height + moving_body_height / 2 + body_size * 0.3 + body_size * 0.05
                    bulb_z = body_size * 0.6  # Position at front face (positive Z = forward)
                    
                    # Cap alpha at 0.8 maximum - use same alpha for bulb and beam for consistency
                    capped_alpha = min(dimmer * 0.4, 0.8)

                    # Render bulb circle facing the beam direction (pure emission, no lighting)
                    self.room_renderer.render_emission_circle(
                        (0.0, bulb_y, bulb_z),
                        bulb_color,
                        bulb_radius,
                        normal=beam_direction,
                        alpha=capped_alpha,
                    )

                    # Render cone beam if dimmer is significant
                    if dimmer > 0.05:
                        beam_length = 15.0
                        beam_alpha = capped_alpha  # Use same alpha as bulb
                        self.room_renderer.render_cone_beam(
                            0.0,
                            bulb_y,
                            bulb_z,
                            beam_direction,
                            bulb_color,
                            length=beam_length,
                            start_radius=bulb_radius * 0.3,
                            end_radius=bulb_radius * 1.2,
                            segments=16,
                            alpha=beam_alpha,
                        )
