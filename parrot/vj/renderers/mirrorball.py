#!/usr/bin/env python3

import math
from typing import Optional, Any

from beartype import beartype

from parrot.fixtures.mirrorball import Mirrorball
from parrot.vj.renderers.base import FixtureRenderer
from parrot.director.frame import Frame


def _rotate_y(
    v: tuple[float, float, float], angle_rad: float
) -> tuple[float, float, float]:
    """Rotate direction around vertical (Y) axis — slowly spins beam pattern."""
    c = math.cos(angle_rad)
    s = math.sin(angle_rad)
    x, y, z = v
    return (c * x + s * z, y, -s * x + c * z)


def _fibonacci_sphere_directions(n: int) -> list[tuple[float, float, float]]:
    """Unit vectors roughly evenly distributed on a sphere (y is vertical in room space)."""
    if n <= 0:
        return []
    directions: list[tuple[float, float, float]] = []
    golden = math.pi * (3.0 - math.sqrt(5.0))
    for i in range(n):
        y = 1.0 - (i / float(max(1, n - 1))) * 2.0
        r_h = math.sqrt(max(0.0, 1.0 - y * y))
        theta = golden * float(i)
        x = math.cos(theta) * r_h
        z = math.sin(theta) * r_h
        length = math.sqrt(x * x + y * y + z * z)
        if length > 1e-6:
            directions.append((x / length, y / length, z / length))
        else:
            directions.append((0.0, 1.0, 0.0))
    return directions


@beartype
class MirrorballRenderer(FixtureRenderer):
    """Chrome sphere with many outward beams when dimmer is up."""

    _NUM_BEAMS = 40

    def __init__(self, fixture: Mirrorball, room_renderer: Optional[Any] = None):
        super().__init__(fixture, room_renderer)
        self._beam_directions = _fibonacci_sphere_directions(self._NUM_BEAMS)

    def _get_default_size(self) -> tuple[float, float]:
        return (36.0, 36.0)

    def render_opaque(self, context, canvas_size: tuple[float, float], frame: Frame) -> None:
        if self.room_renderer is None:
            return

        position_3d = self.get_3d_position(canvas_size)
        sphere_r = self.cube_size * 0.36
        chrome = (0.28, 0.28, 0.3)

        with self.room_renderer.local_position(position_3d):
            with self.room_renderer.local_rotation(self.orientation):
                # Sphere sits on floor; center elevated by radius (y is up in fixture local space).
                self.room_renderer.render_sphere((0.0, sphere_r, 0.0), chrome, radius=sphere_r, alpha=1.0)

        self.render_dmx_address(canvas_size)

    def render_emissive(self, context, canvas_size: tuple[float, float], frame: Frame) -> None:
        if self.room_renderer is None:
            return

        position_3d = self.get_3d_position(canvas_size)
        dimmer = self.get_effective_dimmer(frame)
        if dimmer <= 0.02:
            return

        base_color = self.get_color()
        brightness = 1.0 + dimmer * 2.0
        bulb_color = (
            min(base_color[0] * brightness, 1.0),
            min(base_color[1] * brightness, 1.0),
            min(base_color[2] * brightness, 1.0),
        )
        capped_alpha = min(dimmer * 1.5, 1.0)
        beam_alpha = capped_alpha * 0.22

        sphere_r = self.cube_size * 0.36
        center_y = sphere_r
        beam_len = 5.5
        start_r = sphere_r * 0.06
        end_r = sphere_r * 0.55
        spin = frame.time * 0.12

        with self.room_renderer.local_position(position_3d):
            with self.room_renderer.local_rotation(self.orientation):
                for dx, dy, dz in self._beam_directions:
                    rx, ry, rz = _rotate_y((dx, dy, dz), spin)
                    sx = rx * sphere_r * 0.98
                    sy = center_y + ry * sphere_r * 0.98
                    sz = rz * sphere_r * 0.98
                    self.room_renderer.render_cone_beam(
                        sx,
                        sy,
                        sz,
                        (rx, ry, rz),
                        bulb_color,
                        length=beam_len,
                        start_radius=start_r,
                        end_radius=end_r,
                        segments=10,
                        alpha=beam_alpha,
                    )
