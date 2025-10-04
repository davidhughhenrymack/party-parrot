#!/usr/bin/env python3

from beartype import beartype

from parrot.fixtures.laser import Laser
from parrot.vj.renderers.base import FixtureRenderer
from parrot.vj.renderers.render_utils import SimpleShapeRenderer
from parrot.director.frame import Frame


@beartype
class LaserRenderer(FixtureRenderer):
    """Renderer for laser fixtures with radiating beams"""

    def __init__(self, fixture: Laser):
        super().__init__(fixture)
        self._shape_renderer = None

    def _get_default_size(self) -> tuple[float, float]:
        return (50.0, 50.0)

    def render(self, context, canvas_size: tuple[float, float], frame: Frame):
        """Render laser: gray box (beams TODO)"""
        if self._shape_renderer is None:
            self._shape_renderer = SimpleShapeRenderer(
                context, canvas_size[0], canvas_size[1]
            )

        x, y = self.position
        width, height = self.size

        # Draw gray box
        box_width = width * 0.6
        box_height = height * 0.3
        self._shape_renderer.draw_rectangle(
            x + (width - box_width) / 2,
            y + (height - box_height) / 2,
            box_width,
            box_height,
            color=(0.3, 0.3, 0.3),
            alpha=1.0,
        )
