#!/usr/bin/env python3
"""
3D fixture renderer that draws fixtures as cubes in a room setup.
"""

from beartype import beartype
from parrot.fixtures.base import FixtureBase
from parrot.vj.renderers.base import FixtureRenderer
from parrot.vj.renderers.room_3d import Room3DRenderer
from parrot.director.frame import Frame


@beartype
class Fixture3DRenderer(FixtureRenderer):
    """3D renderer for fixtures as cubes in room space"""

    def __init__(self, fixture: FixtureBase, room_renderer: Room3DRenderer):
        super().__init__(fixture)
        self.room_renderer = room_renderer
        self.cube_size = 0.8  # Size of the fixture cube

    def _get_default_size(self) -> tuple[float, float]:
        """Size not used in 3D rendering"""
        return (1.0, 1.0)

    def render(self, context, canvas_size: tuple[float, float], frame: Frame):
        """Render fixture as 3D cube in room space"""
        # Convert 2D position to 3D room coordinates
        x, y = self.position
        room_x, room_y, room_z = self.room_renderer.convert_2d_to_3d(
            x, y, canvas_size[0], canvas_size[1]
        )

        # Get fixture color and dimmer
        color = self.get_color()
        dimmer = self.get_effective_dimmer(frame)

        # Always render with at least minimum brightness so fixtures don't disappear
        # When dark, show as dim gray outline
        min_brightness = 0.1  # Minimum visibility when fully dark

        if dimmer < 0.01:
            # Fixture is dark - show as dim gray cube
            render_color = (min_brightness, min_brightness, min_brightness)
        else:
            # Apply dimmer to color brightness, ensuring minimum visibility
            brightness = max(dimmer, min_brightness)
            render_color = (
                color[0] * brightness,
                color[1] * brightness,
                color[2] * brightness,
            )

        # Always render the fixture
        self.room_renderer.render_fixture_cube(
            room_x,
            room_y + self.cube_size / 2,
            room_z,  # Position cube on floor
            render_color,
            self.cube_size,
        )
