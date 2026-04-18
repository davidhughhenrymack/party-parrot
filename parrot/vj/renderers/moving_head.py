#!/usr/bin/env python3

from beartype import beartype
from typing import Optional, Any
import math

from parrot.fixtures.moving_head import MovingHead
from parrot.vj.renderers.base import (
    FixtureRenderer,
    quaternion_from_axis_angle,
    quaternion_multiply,
    quaternion_rotate_vector,
)
from parrot.director.frame import Frame
import numpy as np

# Typical moving-head tilt sweep is a little past 180° (front → up → back). DMX may report
# up to ~270°; clamp before scaling so the proxy mesh/beam do not fold past a believable range.
_MECHANICAL_TILT_MAX_DEG = 200.0


@beartype
class MovingHeadRenderer(FixtureRenderer):
    """3D Renderer for moving head fixtures - gray body + sphere + beam (TODO)"""

    def __init__(self, fixture: MovingHead, room_renderer: Optional[Any] = None):
        super().__init__(fixture, room_renderer)

    def _get_default_size(self) -> tuple[float, float]:
        return (40.0, 40.0)

    def _pan_tilt_radians_for_render(self) -> tuple[float, float]:
        """Pan/tilt radians for mesh, bulb, and beam (same convention as historical renderer)."""
        pan_deg = float(self.fixture.get_pan_angle())
        tilt_deg = max(0.0, min(float(self.fixture.get_tilt_angle()), _MECHANICAL_TILT_MAX_DEG))
        pan_rad = math.radians(pan_deg) * 0.5 + math.pi
        tilt_rad = math.radians(tilt_deg) * 0.5
        return pan_rad, tilt_rad

    def render_opaque(self, context, canvas_size: tuple[float, float], frame: Frame):
        """Render only the opaque Blinn-Phong parts (fixed base + moving body)"""
        if self.room_renderer is None:
            return

        # Get 3D position (center of fixture)
        position_3d = self.get_3d_position(canvas_size)

        body_size = self.cube_size * 0.4
        body_color = (0.3, 0.3, 0.3)
        base_height = body_size * 0.42
        moving_body_height = body_size * 0.5
        moving_body_width = body_size * 0.5
        moving_body_depth = body_size * 1.2
        moving_body_y = base_height + moving_body_height / 2 + body_size * 0.3

        pan_rad, tilt_rad = self._pan_tilt_radians_for_render()

        y_axis = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        x_axis = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        pan_quat = quaternion_from_axis_angle(y_axis, pan_rad)
        tilt_quat = quaternion_from_axis_angle(x_axis, tilt_rad)
        moving_body_rotation = quaternion_multiply(tilt_quat, pan_quat)

        half_depth = moving_body_depth * 0.5
        pivot_local = np.array([0.0, 0.0, half_depth], dtype=np.float32)
        pivot_delta = quaternion_rotate_vector(
            self.orientation,
            pivot_local - quaternion_rotate_vector(moving_body_rotation, pivot_local),
        )
        body_position = (
            position_3d[0] + float(pivot_delta[0]),
            position_3d[1] + float(pivot_delta[1]),
            position_3d[2] + float(pivot_delta[2]),
        )

        # Fixed base at fixture position
        with self.room_renderer.local_position(position_3d):
            with self.room_renderer.local_rotation(self.orientation):
                base_width = body_size * 1.2
                base_depth = body_size * 0.8
                self.room_renderer.render_rectangular_box(
                    0.0,
                    base_height / 2,
                    0.0,
                    body_color,
                    base_width,
                    base_height,
                    base_depth,
                )

        # Moving head: pan/tilt about the rear face of the head cuboid (not its center)
        with self.room_renderer.local_position(body_position):
            with self.room_renderer.local_rotation(self.orientation):
                with self.room_renderer.local_rotation(moving_body_rotation):
                    self.room_renderer.render_rectangular_box(
                        0.0,
                        moving_body_y,
                        0.0,
                        body_color,
                        moving_body_width,
                        moving_body_height,
                        moving_body_depth,
                    )

        # Render DMX address
        self.render_dmx_address(canvas_size)

    def render_emissive(self, context, canvas_size: tuple[float, float], frame: Frame):
        """Render only the emissive parts (bulb and beam)"""
        if self.room_renderer is None:
            return

        position_3d = self.get_3d_position(canvas_size)

        body_size = self.cube_size * 0.4
        base_height = body_size * 0.42
        moving_body_height = body_size * 0.5
        moving_body_depth = body_size * 1.2

        bulb_radius = body_size * 0.3
        bulb_color = self.get_color()
        dimmer = self.get_effective_dimmer(frame)

        pan_rad, tilt_rad = self._pan_tilt_radians_for_render()

        cos_tilt = math.cos(tilt_rad)
        sin_tilt = math.sin(tilt_rad)
        cos_pan = math.cos(pan_rad)
        sin_pan = math.sin(pan_rad)

        beam_dir_x = sin_pan * cos_tilt
        beam_dir_y = -sin_tilt
        beam_dir_z = cos_pan * cos_tilt
        beam_direction = (beam_dir_x, beam_dir_y, beam_dir_z)

        y_axis = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        x_axis = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        pan_quat = quaternion_from_axis_angle(y_axis, pan_rad)
        tilt_quat = quaternion_from_axis_angle(x_axis, tilt_rad)
        moving_body_rotation = quaternion_multiply(tilt_quat, pan_quat)

        half_depth = moving_body_depth * 0.5
        pivot_local = np.array([0.0, 0.0, half_depth], dtype=np.float32)
        pivot_delta = quaternion_rotate_vector(
            self.orientation,
            pivot_local - quaternion_rotate_vector(moving_body_rotation, pivot_local),
        )
        body_position = (
            position_3d[0] + float(pivot_delta[0]),
            position_3d[1] + float(pivot_delta[1]),
            position_3d[2] + float(pivot_delta[2]),
        )

        with self.room_renderer.local_position(body_position):
            with self.room_renderer.local_rotation(self.orientation):
                with self.room_renderer.local_rotation(moving_body_rotation):
                    bulb_y = (
                        base_height
                        + moving_body_height / 2
                        + body_size * 0.3
                        + body_size * 0.05
                    )
                    bulb_z = body_size * 0.6

                    brightness_multiplier = 1.0 + dimmer * 2.0
                    boosted_bulb_color = (
                        min(bulb_color[0] * brightness_multiplier, 1.0),
                        min(bulb_color[1] * brightness_multiplier, 1.0),
                        min(bulb_color[2] * brightness_multiplier, 1.0),
                    )

                    capped_alpha = min(dimmer * 1.5, 1.0)

                    self.room_renderer.render_emission_circle(
                        (0.0, bulb_y, bulb_z),
                        boosted_bulb_color,
                        bulb_radius,
                        normal=beam_direction,
                        alpha=capped_alpha,
                    )

                    if dimmer > 0.05:
                        beam_length = 15.0
                        beam_alpha = capped_alpha
                        self.room_renderer.render_cone_beam(
                            0.0,
                            bulb_y,
                            bulb_z,
                            beam_direction,
                            boosted_bulb_color,
                            length=beam_length,
                            start_radius=bulb_radius * 0.3,
                            end_radius=bulb_radius * 1.2,
                            segments=16,
                            alpha=beam_alpha,
                        )
