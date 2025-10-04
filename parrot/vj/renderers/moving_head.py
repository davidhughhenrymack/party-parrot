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
        """Render moving head in 3D: gray body + colored sphere bulb on audience side"""
        if self.room_renderer is None:
            return

        # Get 3D position (center of fixture)
        room_x, room_y, room_z = self.get_3d_position(canvas_size)

        # Render gray body cube
        body_size = self.cube_size * 0.7
        body_color = (0.3, 0.3, 0.3)
        self.room_renderer.render_fixture_cube(
            room_x,
            room_y + body_size / 2,
            room_z,
            body_color,
            body_size,
        )

        # Render colored light sphere bulb on audience-facing side
        bulb_radius = body_size * 0.4
        bulb_distance = body_size * 0.8  # Distance from center toward audience

        # Local offset: forward toward audience
        local_offset = (0.0, 0.0, bulb_distance)
        world_offset = self.get_oriented_offset(local_offset)

        bulb_x = room_x + world_offset[0]
        bulb_y = room_y + body_size + world_offset[1]
        bulb_z = room_z + world_offset[2]
        bulb_color = self.get_render_color(frame, is_bulb=True)  # Brighter

        self.room_renderer.render_sphere(
            bulb_x, bulb_y, bulb_z, bulb_color, bulb_radius
        )
