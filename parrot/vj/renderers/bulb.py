#!/usr/bin/env python3

from beartype import beartype
from typing import Optional, Any

from parrot.fixtures.base import FixtureBase
from parrot.vj.renderers.base import FixtureRenderer
from parrot.director.frame import Frame


@beartype
class BulbRenderer(FixtureRenderer):
    """3D Renderer for simple bulb/PAR fixtures - gray cube body with colored sphere bulb"""

    def __init__(self, fixture: FixtureBase, room_renderer: Optional[Any] = None):
        super().__init__(fixture, room_renderer)

    def _get_default_size(self) -> tuple[float, float]:
        return (30.0, 30.0)

    def render(self, context, canvas_size: tuple[float, float], frame: Frame):
        """Render bulb in 3D: gray cube body + colored sphere on audience side"""
        if self.room_renderer is None:
            return

        # Get 3D position (center of fixture)
        room_x, room_y, room_z = self.get_3d_position(canvas_size)

        # Render gray body cube (small, compact fixture)
        body_size = self.cube_size * 0.6
        body_color = (0.3, 0.3, 0.3)  # Dark gray
        self.room_renderer.render_fixture_cube(
            room_x, room_y + body_size / 2, room_z, body_color, body_size
        )

        # Render colored bulb sphere on audience-facing side (+Z in local coords)
        bulb_radius = body_size * 0.5
        bulb_distance = body_size * 0.7  # Distance from center toward audience

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
