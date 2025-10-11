#!/usr/bin/env python3

from beartype import beartype
from typing import Optional, Any
import numpy as np
import math

from parrot.fixtures.motionstrip import Motionstrip
from parrot.vj.renderers.base import FixtureRenderer, quaternion_from_axis_angle
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
        # Default implementation calls both passes
        self.render_opaque(context, canvas_size, frame)
        self.render_transparent(context, canvas_size, frame)

    def _get_pan_rotation(self) -> float:
        """Calculate pan rotation angle in degrees based on fixture's pan value.
        Pan 0 -> +90°, Pan 255 -> -90° (flipped)

        Note: The fixture's set_pan() already handles invert_pan by inverting the DMX value,
        so we just normalize the stored DMX value and convert to rotation."""
        from parrot.fixtures.motionstrip import Motionstrip38

        fixture = self.fixture

        # Read the DMX pan value from the fixture (already inverted if invert_pan=True)
        pan_dmx_value = fixture.values[0]

        # Motionstrip38 has pan_lower, pan_upper properties
        if isinstance(fixture, Motionstrip38):
            pan_range = fixture.pan_range

            if pan_range > 0:
                normalized_pan = (pan_dmx_value - fixture.pan_lower) / pan_range
            else:
                normalized_pan = 0.0
        else:
            # Default: assume 0-255 range for base Motionstrip
            normalized_pan = pan_dmx_value / 255.0

        # Convert to rotation angle: 1.0 -> -90°, 0 -> +90° (flipped)
        rotation_deg = -90.0 + (1.0 - normalized_pan) * 180.0

        return rotation_deg

    def render_opaque(self, context, canvas_size: tuple[float, float], frame: Frame):
        """Render only the opaque parts (box body and bulb circles)"""
        if self.room_renderer is None:
            return

        # Get 3D position (center of fixture)
        position_3d = self.get_3d_position(canvas_size)

        # Calculate pan rotation and create quaternion for X-axis rotation (fixture's long axis)
        pan_rotation_deg = self._get_pan_rotation()
        pan_rotation_rad = math.radians(pan_rotation_deg)
        x_axis = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        pan_quaternion = quaternion_from_axis_angle(x_axis, pan_rotation_rad)

        # Render with local transforms
        with self.room_renderer.local_position(position_3d):
            with self.room_renderer.local_rotation(self.orientation):
                # Apply pan rotation around X-axis (fixture's long axis with bulbs)
                with self.room_renderer.local_rotation(pan_quaternion):
                    # Render gray body as rectangular box matching bulb layout
                    body_height = self.cube_size * 0.2
                    body_width = self._num_bulbs * 0.22
                    body_depth = self.cube_size * 0.3
                    body_color = (0.2, 0.2, 0.2)

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

                    # Render all bulb circles
                    bulb_spacing = 0.22
                    start_offset_x = -(self._num_bulbs - 1) * bulb_spacing / 2
                    bulb_radius = 0.1
                    bulb_forward_distance = body_depth * 0.7

                    bulbs = self.fixture.get_bulbs()

                    for i, bulb in enumerate(bulbs):
                        try:
                            bulb_color_obj = bulb.get_color()
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
                                r, g, b = (1.0, 1.0, 1.0)

                            bulb_dimmer = bulb.get_dimmer() / 255.0
                            fixture_dimmer = self.get_dimmer()
                            effective_alpha = bulb_dimmer * fixture_dimmer
                            bulb_color = (r, g, b)

                            bulb_x_local = start_offset_x + i * bulb_spacing
                            bulb_y_local = body_height / 2
                            bulb_z_local = bulb_forward_distance

                            # Render just the bulb circle (no beam)
                            self.room_renderer.render_circle(
                                (bulb_x_local, bulb_y_local, bulb_z_local),
                                bulb_color,
                                bulb_radius,
                                normal=(0.0, 0.0, 1.0),
                                alpha=effective_alpha,
                            )
                        except:
                            pass

        # Render DMX address
        self.render_dmx_address(canvas_size)

    def render_transparent(
        self, context, canvas_size: tuple[float, float], frame: Frame
    ):
        """Render only the transparent parts (beams)"""
        if self.room_renderer is None:
            return

        # Get 3D position (center of fixture)
        position_3d = self.get_3d_position(canvas_size)

        # Calculate pan rotation and create quaternion for X-axis rotation (fixture's long axis)
        pan_rotation_deg = self._get_pan_rotation()
        pan_rotation_rad = math.radians(pan_rotation_deg)
        x_axis = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        pan_quaternion = quaternion_from_axis_angle(x_axis, pan_rotation_rad)

        # Render with local transforms
        with self.room_renderer.local_position(position_3d):
            with self.room_renderer.local_rotation(self.orientation):
                # Apply pan rotation around X-axis (fixture's long axis with bulbs)
                with self.room_renderer.local_rotation(pan_quaternion):
                    body_height = self.cube_size * 0.2
                    body_depth = self.cube_size * 0.3
                    bulb_spacing = 0.22
                    start_offset_x = -(self._num_bulbs - 1) * bulb_spacing / 2
                    bulb_radius = 0.1
                    bulb_forward_distance = body_depth * 0.7

                    bulbs = self.fixture.get_bulbs()

                    for i, bulb in enumerate(bulbs):
                        try:
                            bulb_color_obj = bulb.get_color()
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
                                r, g, b = (1.0, 1.0, 1.0)

                            bulb_dimmer = bulb.get_dimmer() / 255.0
                            fixture_dimmer = self.get_dimmer()
                            effective_alpha = bulb_dimmer * fixture_dimmer
                            bulb_color = (r, g, b)

                            bulb_x_local = start_offset_x + i * bulb_spacing
                            bulb_y_local = body_height / 2
                            bulb_z_local = bulb_forward_distance

                            # Render only the beam if dimmer is significant
                            if effective_alpha > 0.05:
                                beam_direction = (
                                    0.0,
                                    0.0,
                                    1.0,
                                )  # Forward in local space
                                beam_length = 6.0
                                self.room_renderer.render_cone_beam(
                                    bulb_x_local,
                                    bulb_y_local,
                                    bulb_z_local,
                                    beam_direction,
                                    bulb_color,
                                    length=beam_length,
                                    start_radius=bulb_radius * 0.3,
                                    end_radius=bulb_radius * 3.0,
                                    segments=16,
                                    alpha=effective_alpha
                                    * 0.4,  # Match moving head alpha calculation
                                )
                        except:
                            pass
