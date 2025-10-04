#!/usr/bin/env python3

from beartype import beartype
from typing import Optional, Any

from parrot.fixtures.laser import Laser
from parrot.vj.renderers.base import FixtureRenderer
from parrot.director.frame import Frame


@beartype
class LaserRenderer(FixtureRenderer):
    """3D Renderer for laser fixtures - gray body with beam (TODO)"""

    def __init__(self, fixture: Laser, room_renderer: Optional[Any] = None):
        super().__init__(fixture, room_renderer)

    def _get_default_size(self) -> tuple[float, float]:
        return (50.0, 50.0)

    def render(self, context, canvas_size: tuple[float, float], frame: Frame):
        """Render laser in 3D: gray box body (beams TODO)"""
        if self.room_renderer is None:
            return

        # Get 3D position
        room_x, room_y, room_z = self.get_3d_position(canvas_size)

        # Render gray body cube
        body_color = (0.3, 0.3, 0.3)
        self.room_renderer.render_fixture_cube(
            room_x,
            room_y + self.cube_size / 2,
            room_z,
            body_color,
            self.cube_size * 0.5,
        )
