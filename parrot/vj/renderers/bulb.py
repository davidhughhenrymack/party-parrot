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
        position_3d = self.get_3d_position(canvas_size)

        # Render with local transforms - much cleaner!
        with self.room_renderer.local_position(position_3d):
            with self.room_renderer.local_rotation(self.orientation):
                # Render gray body cube (small, compact fixture)
                body_size = self.cube_size * 0.6
                body_color = (0.3, 0.3, 0.3)  # Dark gray

                # Body sits on floor (y=0 to y=body_size)
                self.room_renderer.render_cube(
                    (0.0, body_size / 2, 0.0), body_color, body_size
                )

                # Render colored bulb circle with beam on audience-facing side (+Z in local coords)
                bulb_radius = body_size * 0.5
                bulb_distance = body_size * 0.7  # Distance from center toward audience

                # Use full color with dimmer as alpha (transparency)
                bulb_color = self.get_color()  # Full RGB color
                dimmer = self.get_effective_dimmer(frame)

                # Bulb position in local coordinates (at body height, forward toward audience)
                # Normal points forward in +Z (toward audience)
                self.room_renderer.render_bulb_with_beam(
                    (0.0, body_size, bulb_distance),
                    bulb_color,
                    bulb_radius=bulb_radius,
                    normal=(0.0, 0.0, 1.0),  # Face forward toward audience
                    alpha=dimmer,
                    beam_length=8.0,
                )
