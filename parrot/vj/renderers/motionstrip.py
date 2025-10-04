#!/usr/bin/env python3

from beartype import beartype

from parrot.fixtures.motionstrip import Motionstrip
from parrot.vj.renderers.base import FixtureRenderer
from parrot.vj.renderers.render_utils import SimpleShapeRenderer
from parrot.director.frame import Frame

BULB_DIA = 8.0
BULB_MARGIN = 2.0


@beartype
class MotionstripRenderer(FixtureRenderer):
    """Renderer for motion strip fixtures with multiple bulbs"""

    def __init__(self, fixture: Motionstrip):
        self._num_bulbs = len(fixture.get_bulbs())
        super().__init__(fixture)
        self._shape_renderer = None

    def _get_default_size(self) -> tuple[float, float]:
        width = (
            BULB_MARGIN * 2
            + BULB_MARGIN * (self._num_bulbs - 1)
            + BULB_DIA * self._num_bulbs
        )
        height = BULB_MARGIN * 2 + BULB_DIA
        return (width, height)

    def render(self, context, canvas_size: tuple[float, float], frame: Frame):
        """Render motionstrip: gray box with row of colored bulbs"""
        if self._shape_renderer is None:
            self._shape_renderer = SimpleShapeRenderer(
                context, canvas_size[0], canvas_size[1]
            )

        x, y = self.position
        width, height = self.size

        # Draw dark gray background
        self._shape_renderer.draw_rectangle(
            x, y, width, height, color=(0.2, 0.2, 0.2), alpha=1.0
        )

        # Draw each bulb
        bulb_spacing = BULB_DIA + BULB_MARGIN
        start_x = x + BULB_MARGIN + BULB_DIA / 2
        bulb_y = y + height / 2

        for i, bulb in enumerate(self.fixture.get_bulbs()):
            bulb_x = start_x + i * bulb_spacing

            # Get bulb color and dimmer
            try:
                bulb_color = bulb.get_color()
                r, g, b = (
                    bulb_color.r / 255.0,
                    bulb_color.g / 255.0,
                    bulb_color.b / 255.0,
                )
                bulb_dimmer = bulb.get_dimmer() / 255.0
                dimmer = self.get_dimmer()  # Overall strip dimmer

                effective_dimmer = bulb_dimmer * dimmer

                if effective_dimmer > 0.01:
                    dimmed_color = (
                        r * effective_dimmer,
                        g * effective_dimmer,
                        b * effective_dimmer,
                    )
                    self._shape_renderer.draw_circle(
                        bulb_x, bulb_y, BULB_DIA / 2, color=dimmed_color, alpha=1.0
                    )
            except:
                pass
