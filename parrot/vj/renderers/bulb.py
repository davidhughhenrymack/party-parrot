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
                # PAR / theatre can: elongated along beam (Z), roughly square cross-section (X × Y)
                body_size = self.cube_size * 0.4
                body_width = body_size
                body_height = body_size * 1.05
                body_depth = body_size * 2.25
                body_color = (0.3, 0.3, 0.3)  # Dark gray

                # Body sits on floor, centered; depth is the long housing axis
                self.room_renderer.render_rectangular_box(
                    0.0, body_height / 2, 0.0, body_color, body_width, body_height, body_depth
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
                body_size = self.cube_size * 0.4
                body_height = body_size * 1.05
                body_depth = body_size * 2.25
                half_depth = body_depth * 0.5
                bulb_radius = body_size * 0.42
                base_color = self.get_color()
                dimmer = self.get_effective_dimmer(frame)

                # Boost brightness and saturate towards white at high dimmer
                # Brightness multiplier increases with dimmer to saturate towards white
                brightness_multiplier = 1.0 + dimmer * 2.0  # 1.0 at 0%, up to 3.0 at 100%
                bulb_color = (
                    min(base_color[0] * brightness_multiplier, 1.0),
                    min(base_color[1] * brightness_multiplier, 1.0),
                    min(base_color[2] * brightness_multiplier, 1.0),
                )

                # Increased alpha for better visibility - boost significantly
                capped_alpha = min(dimmer * 1.5, 1.0)

                # Lens on front face (room box front at z - half_depth); beam along -Z
                bulb_y = body_height
                bulb_z = -half_depth - body_size * 0.02
                self.room_renderer.render_emission_circle(
                    (0.0, bulb_y, bulb_z),
                    bulb_color,
                    bulb_radius,
                    normal=(0.0, 0.0, -1.0),
                    alpha=capped_alpha,
                )

                # Render beam if dimmer is significant
                if dimmer > 0.05:
                    beam_direction = (0.0, 0.0, -1.0)
                    beam_length = 8.0
                    beam_alpha = capped_alpha  # Use same alpha as bulb
                    self.room_renderer.render_cone_beam(
                        0.0,
                        bulb_y,
                        bulb_z,
                        beam_direction,
                        bulb_color,
                        length=beam_length,
                        start_radius=bulb_radius * 0.3,
                        end_radius=bulb_radius * 3.0,
                        segments=16,
                        alpha=beam_alpha,
                    )
