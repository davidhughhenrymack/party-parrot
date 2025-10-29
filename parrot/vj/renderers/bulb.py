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

    def render_opaque(self, context, canvas_size: tuple[float, float], frame: Frame):
        """Render only the opaque Blinn-Phong parts (cube body)"""
        if self.room_renderer is None:
            return

        # Get 3D position (center of fixture)
        position_3d = self.get_3d_position(canvas_size)

        # Render with local transforms
        with self.room_renderer.local_position(position_3d):
            with self.room_renderer.local_rotation(self.orientation):
                # Render gray body cube (small, compact fixture)
                body_size = self.cube_size * 0.6
                body_color = (0.3, 0.3, 0.3)  # Dark gray

                # Body sits on floor (y=0 to y=body_size)
                self.room_renderer.render_cube(
                    (0.0, body_size / 2, 0.0), body_color, body_size
                )

        # Render DMX address
        self.render_dmx_address(canvas_size)

    def render_emissive(self, context, canvas_size: tuple[float, float], frame: Frame):
        """Render only the emissive parts (bulb and beam)"""
        if self.room_renderer is None:
            return

        # Get 3D position (center of fixture)
        position_3d = self.get_3d_position(canvas_size)

        # Render with local transforms
        with self.room_renderer.local_position(position_3d):
            with self.room_renderer.local_rotation(self.orientation):
                body_size = self.cube_size * 0.6
                bulb_radius = body_size * 0.3  # Increased size for visibility
                bulb_distance = body_size * 0.7
                bulb_color = self.get_color()
                dimmer = self.get_effective_dimmer(frame)

                # Increased alpha for better visibility
                capped_alpha = min(dimmer * 0.8, 1.0)

                # Render colored bulb circle (pure emission, no lighting)
                self.room_renderer.render_emission_circle(
                    (0.0, body_size, bulb_distance),
                    bulb_color,
                    bulb_radius,
                    normal=(0.0, 0.0, 1.0),  # Face forward
                    alpha=capped_alpha,
                )

                # Render beam if dimmer is significant
                if dimmer > 0.05:
                    beam_direction = (0.0, 0.0, 1.0)  # Forward in local space
                    beam_length = 8.0
                    beam_alpha = capped_alpha  # Use same alpha as bulb
                    self.room_renderer.render_cone_beam(
                        0.0,
                        body_size,
                        bulb_distance,
                        beam_direction,
                        bulb_color,
                        length=beam_length,
                        start_radius=bulb_radius * 0.3,
                        end_radius=bulb_radius * 3.0,
                        segments=16,
                        alpha=beam_alpha,
                    )
