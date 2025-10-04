#!/usr/bin/env python3

from beartype import beartype

from parrot.fixtures.base import FixtureBase
from parrot.vj.renderers.base import FixtureRenderer
from parrot.vj.renderers.render_utils import SimpleShapeRenderer
from parrot.director.frame import Frame


@beartype
class BulbRenderer(FixtureRenderer):
    """Renderer for simple bulb/PAR fixtures - circle with color.
    Mimics legacy GUI: gray box with lit circle."""

    def __init__(self, fixture: FixtureBase):
        super().__init__(fixture)
        self._shape_renderer = None

    def _get_default_size(self) -> tuple[float, float]:
        return (30.0, 30.0)

    def render(self, context, canvas_size: tuple[float, float], frame: Frame):
        """Render bulb: gray box with colored circle that lights up"""
        # Create shape renderer if needed
        if self._shape_renderer is None:
            self._shape_renderer = SimpleShapeRenderer(
                context, canvas_size[0], canvas_size[1]
            )

        x, y = self.position
        width, height = self.size

        # Draw gray background box
        self._shape_renderer.draw_rectangle(
            x, y, width, height, color=(0.3, 0.3, 0.3), alpha=1.0
        )

        # Draw colored circle with dimmer effect
        color = self.get_color()
        dimmer = self.get_effective_dimmer(frame)

        if dimmer > 0.01:
            # Draw bulb circle at center
            cx = x + width / 2.0
            cy = y + height / 2.0
            radius = min(width, height) * 0.4

            # Apply dimmer to color brightness
            dimmed_color = (color[0] * dimmer, color[1] * dimmer, color[2] * dimmer)

            self._shape_renderer.draw_circle(
                cx, cy, radius, color=dimmed_color, alpha=1.0
            )
