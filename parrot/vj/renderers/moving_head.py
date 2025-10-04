#!/usr/bin/env python3

from beartype import beartype
import math

from parrot.fixtures.moving_head import MovingHead
from parrot.vj.renderers.base import FixtureRenderer
from parrot.vj.renderers.render_utils import SimpleShapeRenderer
from parrot.director.frame import Frame


@beartype
class MovingHeadRenderer(FixtureRenderer):
    """Renderer for moving head fixtures with base, head, and beam"""

    def __init__(self, fixture: MovingHead):
        super().__init__(fixture)
        self._shape_renderer = None

    def _get_default_size(self) -> tuple[float, float]:
        return (40.0, 40.0)

    def get_angles(self) -> tuple[float, float]:
        """Return pan and tilt angles in radians"""
        pan_rad = math.radians(self.fixture.get_pan_angle())
        tilt_rad = math.radians(self.fixture.get_tilt_angle())
        return pan_rad, tilt_rad

    def render(self, context, canvas_size: tuple[float, float], frame: Frame):
        """Render moving head: base + head + light circle + beam"""
        if self._shape_renderer is None:
            self._shape_renderer = SimpleShapeRenderer(
                context, canvas_size[0], canvas_size[1]
            )

        x, y = self.position
        width, height = self.size

        # Draw gray base at bottom
        base_height = height * 0.25
        self._shape_renderer.draw_rectangle(
            x,
            y + height - base_height,
            width,
            base_height,
            color=(0.3, 0.3, 0.3),
            alpha=1.0,
        )

        # Draw gray head
        head_height = height * 0.625
        self._shape_renderer.draw_rectangle(
            x, y, width, head_height, color=(0.3, 0.3, 0.3), alpha=1.0
        )

        # Draw light circle if on
        color = self.get_color()
        dimmer = self.get_effective_dimmer(frame)

        if dimmer > 0.01:
            cx = x + width / 2.0
            cy = y + height * 0.15
            radius = width * 0.175

            dimmed_color = (color[0] * dimmer, color[1] * dimmer, color[2] * dimmer)
            self._shape_renderer.draw_circle(
                cx, cy, radius, color=dimmed_color, alpha=1.0
            )

            # Draw beam (simple line)
            pan, tilt = self.get_angles()
            beam_length = 20.0
            end_x = cx + beam_length * math.cos(pan)
            end_y = cy + beam_length * math.sin(tilt)
            self._shape_renderer.draw_line(
                cx, cy, end_x, end_y, color=dimmed_color, alpha=0.7, width=3.0
            )
