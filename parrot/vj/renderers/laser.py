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
