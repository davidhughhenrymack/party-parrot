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
        """Render motionstrip in 3D: gray body + row of 8 colored sphere bulbs"""
        if self.room_renderer is None:
            return

        # Get 3D position
        room_x, room_y, room_z = self.get_3d_position(canvas_size)

        # Render gray body as rectangular box matching bulb layout
        body_height = self.cube_size * 0.2
        body_width = self._num_bulbs * 0.22  # Match bulb spacing
        body_depth = self.cube_size * 0.3
        body_color = (0.2, 0.2, 0.2)  # Dark gray

        # Render rectangular base
        self.room_renderer.render_rectangular_box(
            room_x,
            room_y + body_height / 2,
            room_z,
            body_color,
            body_width,
            body_height,
            body_depth,
        )

        # Render all bulb spheres in a row - ensure all 8 are visible
        bulb_spacing = 0.22  # Space them out more
        start_offset = -(self._num_bulbs - 1) * bulb_spacing / 2
        bulb_radius = 0.1  # Make them slightly bigger
        bulb_height_offset = body_height * 1.2  # Raise them higher

        bulbs = self.fixture.get_bulbs()

        for i, bulb in enumerate(bulbs):
            bulb_x = room_x + start_offset + i * bulb_spacing
            bulb_y = room_y + bulb_height_offset + bulb_radius

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

                bulb_dimmer = bulb.get_dimmer() / 255.0
                dimmer = self.get_dimmer()

                # Make bulbs brighter like PARs
                effective_dimmer = max(bulb_dimmer * dimmer * 1.5, 0.1)
                effective_dimmer = min(effective_dimmer, 1.0)

                bulb_color = (
                    r * effective_dimmer,
                    g * effective_dimmer,
                    b * effective_dimmer,
                )

                self.room_renderer.render_sphere(
                    bulb_x, bulb_y, room_z, bulb_color, bulb_radius
                )
            except:
                pass
