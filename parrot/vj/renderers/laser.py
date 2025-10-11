#!/usr/bin/env python3

from beartype import beartype
from typing import Optional, Any
import math

from parrot.fixtures.laser import Laser
from parrot.vj.renderers.base import FixtureRenderer
from parrot.director.frame import Frame


@beartype
class LaserRenderer(FixtureRenderer):
    """3D Renderer for laser fixtures - gray body with 12 fanning white beams"""

    def __init__(self, fixture: Laser, room_renderer: Optional[Any] = None):
        super().__init__(fixture, room_renderer)

    def _get_default_size(self) -> tuple[float, float]:
        return (50.0, 50.0)

    def render(self, context, canvas_size: tuple[float, float], frame: Frame):
        """Render laser in 3D: gray box body + 12 fanning white beams"""
        # Default implementation calls both passes
        self.render_opaque(context, canvas_size, frame)
        self.render_transparent(context, canvas_size, frame)

    def render_opaque(self, context, canvas_size: tuple[float, float], frame: Frame):
        """Render only the opaque parts (cube body)"""
        if self.room_renderer is None:
            return

        # Get 3D position (center of fixture)
        position_3d = self.get_3d_position(canvas_size)

        # Render with local transforms
        with self.room_renderer.local_position(position_3d):
            with self.room_renderer.local_rotation(self.orientation):
                # Render gray body cube
                body_size = self.cube_size * 0.5
                body_color = (0.3, 0.3, 0.3)

                # Body sits on floor (y=0 to y=body_size)
                self.room_renderer.render_cube(
                    (0.0, body_size / 2, 0.0), body_color, body_size
                )

        # Render DMX address
        self.render_dmx_address(canvas_size)

    def render_transparent(
        self, context, canvas_size: tuple[float, float], frame: Frame
    ):
        """Render only the transparent parts (12 fanning beams)"""
        if self.room_renderer is None:
            return

        dimmer = self.get_effective_dimmer(frame)

        # Only render beams if dimmer is on
        if dimmer < 0.05:
            return

        # Get 3D position (center of fixture)
        position_3d = self.get_3d_position(canvas_size)

        # Render with local transforms
        with self.room_renderer.local_position(position_3d):
            with self.room_renderer.local_rotation(self.orientation):
                body_size = self.cube_size * 0.5

                # White color for laser beams
                beam_color = (1.0, 1.0, 1.0)

                # 12 beams arranged in a horizontal fan (left to right)
                num_beams = 12
                beam_length = 20.0  # Long narrow beams
                beam_radius = 0.02  # Very narrow beams

                # Animation: sweep the fan pattern side to side
                sweep_speed = 1.5  # Oscillation speed
                sweep_range = math.radians(40)  # Total sweep angle
                sweep_offset = math.sin(frame.time * sweep_speed) * sweep_range

                # Fan spreads horizontally (left to right)
                fan_spread = math.radians(60)  # 60 degree horizontal spread
                upward_tilt = math.radians(15)  # Tilt up to go over audience heads

                for i in range(num_beams):
                    # Angle within the fan (from left to right)
                    # -1 to 1, then map to fan_spread angle
                    fan_position = (i / (num_beams - 1)) - 0.5  # -0.5 to 0.5
                    horizontal_angle = fan_position * fan_spread + sweep_offset

                    # Calculate beam direction in horizontal fan
                    # X component: left to right sweep
                    # Y component: constant upward tilt (above audience)
                    # Z component: forward toward audience
                    beam_x = math.sin(horizontal_angle) * math.cos(upward_tilt)
                    beam_y = math.sin(upward_tilt)
                    beam_z = math.cos(horizontal_angle) * math.cos(upward_tilt)

                    beam_direction = (beam_x, beam_y, beam_z)

                    # Beam starts from top of fixture body
                    beam_start_y = body_size

                    # Render narrow white beam
                    self.room_renderer.render_cone_beam(
                        0.0,
                        beam_start_y,
                        0.0,
                        beam_direction,
                        beam_color,
                        length=beam_length,
                        start_radius=beam_radius,
                        end_radius=beam_radius * 1.5,  # Slight expansion
                        segments=8,  # Fewer segments for narrow beams
                        alpha=dimmer * 0.5,  # Visible beams
                    )
