#!/usr/bin/env python3

from beartype import beartype
from typing import Optional, Any

from parrot.fixtures.motionstrip import Motionstrip
from parrot.vj.renderers.base import FixtureRenderer
from parrot.director.frame import Frame

BULB_DIA = 8.0
BULB_MARGIN = 2.0


@beartype
class MotionstripRenderer(FixtureRenderer):
    """3D Renderer for motion strip fixtures - gray body with multiple colored spheres"""

    def __init__(self, fixture: Motionstrip, room_renderer: Optional[Any] = None):
        self._num_bulbs = len(fixture.get_bulbs())
        super().__init__(fixture, room_renderer)

    def _get_default_size(self) -> tuple[float, float]:
        width = (
            BULB_MARGIN * 2
            + BULB_MARGIN * (self._num_bulbs - 1)
            + BULB_DIA * self._num_bulbs
        )
        height = BULB_MARGIN * 2 + BULB_DIA
        return (width, height)

    def render(self, context, canvas_size: tuple[float, float], frame: Frame):
        """Render motionstrip in 3D: gray body + row of colored sphere bulbs on audience side"""
        if self.room_renderer is None:
            return

        # Get 3D position (center of fixture)
        position_3d = self.get_3d_position(canvas_size)

        # Render with local transforms - much cleaner!
        with self.room_renderer.local_position(position_3d):
            with self.room_renderer.local_rotation(self.orientation):
                # Render gray body as rectangular box matching bulb layout
                body_height = self.cube_size * 0.2
                body_width = self._num_bulbs * 0.22  # Match bulb spacing
                body_depth = self.cube_size * 0.3
                body_color = (0.2, 0.2, 0.2)  # Dark gray

                # Render rectangular base in local coordinates
                self.room_renderer.render_rectangular_box(
                    0.0,
                    body_height / 2,
                    0.0,
                    body_color,
                    body_width,
                    body_height,
                    body_depth,
                )

                # Render all bulb spheres in a row on audience-facing side
                bulb_spacing = 0.22  # Space them out more
                start_offset_x = -(self._num_bulbs - 1) * bulb_spacing / 2
                bulb_radius = 0.1  # Make them slightly bigger
                bulb_forward_distance = body_depth * 0.7  # Distance forward from center

                bulbs = self.fixture.get_bulbs()

                for i, bulb in enumerate(bulbs):
                    try:
                        bulb_color_obj = bulb.get_color()
                        # Handle both Color object and dict formats
                        if hasattr(bulb_color_obj, "red"):
                            r, g, b = (
                                bulb_color_obj.red,
                                bulb_color_obj.green,
                                bulb_color_obj.blue,
                            )
                        elif hasattr(bulb_color_obj, "r"):
                            r, g, b = (
                                bulb_color_obj.r / 255.0,
                                bulb_color_obj.g / 255.0,
                                bulb_color_obj.b / 255.0,
                            )
                        else:
                            r, g, b = (1.0, 1.0, 1.0)  # Default white

                        # Use full color with dimmer as alpha (transparency)
                        bulb_dimmer = bulb.get_dimmer() / 255.0
                        fixture_dimmer = self.get_dimmer()

                        # Combine bulb and fixture dimmer for alpha
                        effective_alpha = bulb_dimmer * fixture_dimmer

                        bulb_color = (r, g, b)  # Full color, not dimmed

                        # Bulb position in local coordinates
                        bulb_x_local = start_offset_x + i * bulb_spacing
                        bulb_y_local = body_height / 2
                        bulb_z_local = bulb_forward_distance

                        self.room_renderer.render_sphere(
                            (bulb_x_local, bulb_y_local, bulb_z_local),
                            bulb_color,
                            bulb_radius,
                            alpha=effective_alpha,
                        )
                    except:
                        pass
