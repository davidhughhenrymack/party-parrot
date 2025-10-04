#!/usr/bin/env python3

from beartype import beartype
from typing import Optional, Any
import math

from parrot.fixtures.moving_head import MovingHead
from parrot.vj.renderers.base import FixtureRenderer
from parrot.director.frame import Frame


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

    def render(self, context, canvas_size: tuple[float, float], frame: Frame):
        """Render moving head in 3D: gray body + colored sphere bulb + beam"""
        if self.room_renderer is None:
            return

        # Get 3D position (center of fixture)
        position_3d = self.get_3d_position(canvas_size)

        # Render with local transforms - much cleaner!
        with self.room_renderer.local_position(position_3d):
            with self.room_renderer.local_rotation(self.orientation):
                # Render gray body cube
                body_size = self.cube_size * 0.7
                body_color = (0.3, 0.3, 0.3)

                # Body sits on floor (y=0 to y=body_size)
                self.room_renderer.render_cube(
                    (0.0, body_size / 2, 0.0), body_color, body_size
                )

                # Render colored light sphere bulb on audience-facing side
                bulb_radius = body_size * 0.4
                bulb_distance = body_size * 0.8  # Distance from center toward audience

                # Use full color with dimmer as alpha (transparency)
                bulb_color = self.get_color()  # Full RGB color
                dimmer = self.get_effective_dimmer(frame)

                # Bulb position in local coordinates (at body height, forward toward audience)
                self.room_renderer.render_sphere(
                    (0.0, body_size, bulb_distance),
                    bulb_color,
                    bulb_radius,
                    alpha=dimmer,
                )

                # Render beam based on pan/tilt/dimmer/color
                # Only render beam if dimmer is above threshold
                if dimmer > 0.05:
                    # Get pan and tilt angles (scaled by 0.5 for more realistic range)
                    pan_rad, tilt_rad = self.get_angles()
                    pan_rad *= 0.5  # Halve the angular range
                    tilt_rad *= 0.5  # Halve the angular range
                    pan_rad += math.pi  # Rotate pan by 180 degrees

                    # Calculate beam direction vector from pan and tilt
                    # Default orientation: pointing toward audience (+Z in local space)
                    # Pan rotates around Y axis (horizontal), Tilt rotates around local X axis (vertical)

                    # Start with default forward direction
                    cos_tilt = math.cos(tilt_rad)
                    sin_tilt = math.sin(tilt_rad)
                    cos_pan = math.cos(pan_rad)
                    sin_pan = math.sin(pan_rad)

                    # Calculate beam direction in world space
                    # Pan rotates left/right, tilt rotates up/down
                    beam_dir_x = sin_pan * cos_tilt
                    beam_dir_y = (
                        -sin_tilt
                    )  # Negative because tilt up should point up (+Y)
                    beam_dir_z = cos_pan * cos_tilt

                    # Get beam color (full brightness, dimmer affects alpha)
                    base_color = self.get_color()
                    beam_color = base_color  # Use full color, not dimmed

                    # Render cone beam from bulb position in local coordinates
                    beam_length = 15.0  # Fixed length regardless of dimmer
                    self.room_renderer.render_cone_beam(
                        0.0,
                        body_size,
                        bulb_distance,
                        (beam_dir_x, beam_dir_y, beam_dir_z),
                        beam_color,
                        length=beam_length,
                        start_radius=bulb_radius * 0.3,
                        end_radius=bulb_radius * 1.2,
                        segments=16,
                        alpha=dimmer,  # Dimmer controls transparency
                    )
