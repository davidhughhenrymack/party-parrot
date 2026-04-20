#!/usr/bin/env python3

from beartype import beartype
from dataclasses import dataclass
from typing import Optional, Any
import math

from parrot.fixtures.moving_head import MovingHead
from parrot.vj.moving_head_visual import pan_radians_for_render, tilt_radians_for_render
from parrot.vj.renderers.base import (
    FixtureRenderer,
    quaternion_from_axis_angle,
    quaternion_multiply,
    quaternion_rotate_vector,
)
from parrot.director.frame import Frame
import numpy as np


@beartype
@dataclass(frozen=True)
class _MovingHeadDimensions:
    """Body dimensions for a moving head in desktop renderer local coords.

    Layout mirrors Parrot Cloud's ``movingHeadDimensions`` in
    ``parrot_cloud/frontend/src/fixtureModels.js`` so the web preview and the
    desktop OpenGL view stay visually consistent.
    """

    base_width: float
    base_height: float
    base_depth: float
    moving_body_width: float
    moving_body_height: float
    moving_body_depth: float
    head_pivot_y: float  # yoke-top pivot in fixture-local (pre-orientation) Y


@beartype
def _moving_head_dimensions(cube_size: float) -> _MovingHeadDimensions:
    body_size = cube_size * 0.4
    base_height = body_size * 0.42
    moving_body_height = body_size * 0.5
    return _MovingHeadDimensions(
        base_width=body_size * 1.2,
        base_height=base_height,
        base_depth=body_size * 0.8,
        moving_body_width=body_size * 0.5,
        moving_body_height=moving_body_height,
        moving_body_depth=body_size * 1.2,
        # Pivot y = top of base + shoulder gap + half head height; matches web's
        # ``baseHeight + headOffsetZ`` (which is itself ``baseHeight + bs*0.3 +
        # headHeight/2``). Rotating pan/tilt around this pivot keeps the head
        # sitting on top of the base at rest, upright for floor movers and
        # hanging below the base for truss-flipped movers.
        head_pivot_y=base_height + body_size * 0.3 + moving_body_height / 2,
    )


@beartype
def _head_pivot_world(
    position_3d: tuple[float, float, float],
    orientation: np.ndarray,
    dims: _MovingHeadDimensions,
) -> tuple[float, float, float]:
    """Where to place ``local_position`` so pan/tilt rotates around the head pivot.

    ``Room3DRenderer.local_position`` REPLACES the current position (it does
    not compose), so we have to collapse the fixture-root translation and the
    pivot offset into a single world coordinate. The pivot offset
    ``(0, head_pivot_y, 0)`` lives in the fixture-local (pre-orientation)
    frame — rotating it by ``self.orientation`` carries it into the room's
    world frame before adding to ``position_3d``.
    """
    local_pivot = np.array([0.0, dims.head_pivot_y, 0.0], dtype=np.float32)
    rotated = quaternion_rotate_vector(orientation, local_pivot)
    return (
        position_3d[0] + float(rotated[0]),
        position_3d[1] + float(rotated[1]),
        position_3d[2] + float(rotated[2]),
    )

# Prism rendering: 7-facet prism. Sub-beams are splayed well off the central
# axis (so the fan is clearly visible, not a tight bundle) and each is drawn
# wider than a single beam to make the prism look chunky and luminous.
_PRISM_FACETS = 7
_PRISM_SPLAY_DEG = 18.0
# Scales `rotate_speed` ([-1,1]) into radians/sec for visual rotation.
_PRISM_ROTATION_RATE_HZ = 0.5

# Focus-to-beam-width mapping. Fixture focus ∈ [0.0 wide, 1.0 tight].
# We scale the beam's end_radius by this factor so a fully-focused beam looks
# like a tight pencil (≈_FOCUS_TIGHT_MULT × the wide width) and a fully-wide
# beam matches the original (unfocused) size.
_FOCUS_WIDE_MULT = 1.0
_FOCUS_TIGHT_MULT = 0.22


def _focus_width_multiplier(focus: float) -> float:
    focus = max(0.0, min(1.0, focus))
    return _FOCUS_WIDE_MULT + (_FOCUS_TIGHT_MULT - _FOCUS_WIDE_MULT) * focus


@beartype
class MovingHeadRenderer(FixtureRenderer):
    """3D Renderer for moving head fixtures - gray body + sphere + beam (TODO)"""

    def __init__(self, fixture: MovingHead, room_renderer: Optional[Any] = None):
        super().__init__(fixture, room_renderer)

    def _get_default_size(self) -> tuple[float, float]:
        return (40.0, 40.0)

    def _pan_tilt_radians_for_render(self) -> tuple[float, float]:
        """Pan/tilt radians for mesh, bulb, and beam — see `parrot.vj.moving_head_visual`."""
        pan_rad = pan_radians_for_render(float(self.output_fixture().get_pan_angle()))
        tilt_rad = tilt_radians_for_render(float(self.output_fixture().get_tilt_angle()))
        return pan_rad, tilt_rad

    def _moving_body_rotation(self) -> np.ndarray:
        """Yoke rotation for the moving head's head cuboid.

        Real moving-head mechanics: the yoke pans around world +Y, then the
        head tilts around the *panned* yoke X-axis. In world/pre-multiply
        quaternion form that is ``pan ∘ tilt`` — i.e. `pan_quat * tilt_quat`
        — applied to the body's local forward (+Z). Using `tilt * pan` here
        made the body and the beam diverge as soon as both pan and tilt were
        non-zero, because the beam direction was computed as pan(tilt(+Z)).
        """
        pan_rad, tilt_rad = self._pan_tilt_radians_for_render()
        y_axis = np.array([0.0, 1.0, 0.0], dtype=np.float32)
        x_axis = np.array([1.0, 0.0, 0.0], dtype=np.float32)
        pan_quat = quaternion_from_axis_angle(y_axis, pan_rad)
        tilt_quat = quaternion_from_axis_angle(x_axis, tilt_rad)
        return quaternion_multiply(pan_quat, tilt_quat)

    def render_opaque(self, context, canvas_size: tuple[float, float], frame: Frame):
        """Render only the opaque Blinn-Phong parts (fixed base + moving body)"""
        if self.room_renderer is None:
            return

        position_3d = self.get_3d_position(canvas_size)

        dims = _moving_head_dimensions(self.cube_size)
        body_color = (0.3, 0.3, 0.3)
        moving_body_rotation = self._moving_body_rotation()

        # Fixed base at fixture position
        with self.room_renderer.local_position(position_3d):
            with self.room_renderer.local_rotation(self.orientation):
                self.room_renderer.render_rectangular_box(
                    0.0,
                    dims.base_height / 2,
                    0.0,
                    body_color,
                    dims.base_width,
                    dims.base_height,
                    dims.base_depth,
                )

                # Neutral-pan indicator: lighter grey slab on the base “front” in
                # `room_3d` box space (face normal −Z; see `render_rectangular_box`).
                # Parrot Cloud’s Z-up base puts the same marker on the −venue-Y face;
                # see `parrot.vj.moving_head_visual` + AGENTS.md. Pan/tilt for mesh/beam
                # use `pan_radians_for_render` / `tilt_radians_for_render` only.
                screen_color = (0.65, 0.65, 0.65)
                screen_thickness = dims.base_depth * 0.08
                screen_width = dims.base_width * 0.55
                screen_height = dims.base_height * 0.55
                self.room_renderer.render_rectangular_box(
                    0.0,
                    dims.base_height / 2,
                    -(dims.base_depth / 2 + screen_thickness / 2),
                    screen_color,
                    screen_width,
                    screen_height,
                    screen_thickness,
                )

        # Head: rotate pan/tilt AROUND the yoke pivot (at the head's center in the
        # fixture-local frame), matching Parrot Cloud's `headPivotGroup` — not
        # around the fixture origin. Previous code offset the head inside the
        # rotated body frame, so the rest -π/2 tilt flung the head box below the
        # base for floor movers and above the yoke for truss-flipped fixtures
        # (see `_head_pivot_world`).
        pivot_world = _head_pivot_world(position_3d, self.orientation, dims)
        with self.room_renderer.local_position(pivot_world):
            with self.room_renderer.local_rotation(self.orientation):
                with self.room_renderer.local_rotation(moving_body_rotation):
                    # Head box centered on the pivot with long axis +Z; the rest
                    # tilt of -π/2 rotates +Z → +Y so the beam exits the TOP of
                    # the head and the box stands upright above the base.
                    self.room_renderer.render_rectangular_box(
                        0.0,
                        -dims.moving_body_height / 2,
                        0.0,
                        body_color,
                        dims.moving_body_width,
                        dims.moving_body_height,
                        dims.moving_body_depth,
                    )

        self.render_dmx_address(canvas_size)

    def render_emissive(self, context, canvas_size: tuple[float, float], frame: Frame):
        """Render only the emissive parts (bulb and beam)"""
        if self.room_renderer is None:
            return

        position_3d = self.get_3d_position(canvas_size)

        dims = _moving_head_dimensions(self.cube_size)
        body_size = self.cube_size * 0.4
        bulb_radius = body_size * 0.3
        bulb_color = self.get_color()
        dimmer = self.get_effective_dimmer(frame)

        moving_body_rotation = self._moving_body_rotation()

        # Bulb/beam origin is expressed in the yoke-pivot frame, on the head's
        # front face (+Z locally). After the rest -π/2 tilt around X, +Z maps
        # to +Y so the lens sits on top of the head. The beam normal uses the
        # same +Z local direction, which the nested rotation stack steers to
        # the correct world aim.
        lens_extension = body_size * 0.05
        bulb_local = (0.0, 0.0, dims.moving_body_depth / 2 + lens_extension)
        beam_direction = (0.0, 0.0, 1.0)

        pivot_world = _head_pivot_world(position_3d, self.orientation, dims)

        with self.room_renderer.local_position(pivot_world):
            with self.room_renderer.local_rotation(self.orientation):
                with self.room_renderer.local_rotation(moving_body_rotation):
                    brightness_multiplier = 1.0 + dimmer * 2.0
                    boosted_bulb_color = (
                        min(bulb_color[0] * brightness_multiplier, 1.0),
                        min(bulb_color[1] * brightness_multiplier, 1.0),
                        min(bulb_color[2] * brightness_multiplier, 1.0),
                    )

                    capped_alpha = min(dimmer * 1.5, 1.0)

                    self.room_renderer.render_emission_circle(
                        bulb_local,
                        boosted_bulb_color,
                        bulb_radius,
                        normal=beam_direction,
                        alpha=capped_alpha,
                    )

                    if dimmer > 0.05:
                        beam_length = 15.0
                        beam_alpha = capped_alpha
                        # `supports_prism` / `supports_focus` let fixtures without
                        # a physical prism accessory (Chauvet Rogue Beam R2) or a
                        # variable-focus optic render as a plain beam even when
                        # interpreters drive the DMX values.
                        if self.output_fixture().supports_prism:
                            prism_on, prism_speed = self.output_fixture().get_prism()
                        else:
                            prism_on, prism_speed = False, 0.0
                        if self.output_fixture().supports_focus:
                            # Fixture focus modulates end_radius: tight focus → narrow
                            # beam, wide focus → the original chunky cone. start_radius
                            # stays put since the lens aperture doesn't visibly change.
                            focus_mult = _focus_width_multiplier(
                                float(self.output_fixture().get_focus())
                            )
                        else:
                            focus_mult = _FOCUS_WIDE_MULT

                        if prism_on:
                            # Split the beam into N splayed copies around the central axis.
                            rotation_phase = (
                                frame.time * prism_speed * _PRISM_ROTATION_RATE_HZ * 2.0 * math.pi
                            )
                            # Each splayed sub-beam is chunkier than the plain beam so the
                            # prism fan reads as "wide light", and they share the larger
                            # splay angle above for a clearly-fanned look.
                            sub_start_r = bulb_radius * 0.3
                            sub_end_r = bulb_radius * 1.4 * focus_mult
                            for i in range(_PRISM_FACETS):
                                theta = (
                                    2.0 * math.pi * i / _PRISM_FACETS + rotation_phase
                                )
                                dir_splayed = _splay_direction(
                                    beam_direction, _PRISM_SPLAY_DEG, theta
                                )
                                self.room_renderer.render_cone_beam(
                                    bulb_local[0],
                                    bulb_local[1],
                                    bulb_local[2],
                                    dir_splayed,
                                    boosted_bulb_color,
                                    length=beam_length,
                                    start_radius=sub_start_r,
                                    end_radius=sub_end_r,
                                    segments=12,
                                    alpha=beam_alpha,
                                )
                        else:
                            self.room_renderer.render_cone_beam(
                                bulb_local[0],
                                bulb_local[1],
                                bulb_local[2],
                                beam_direction,
                                boosted_bulb_color,
                                length=beam_length,
                                start_radius=bulb_radius * 0.3,
                                end_radius=bulb_radius * 1.2 * focus_mult,
                                segments=16,
                                alpha=beam_alpha,
                            )


def _splay_direction(
    axis: tuple[float, float, float], splay_deg: float, theta: float
) -> tuple[float, float, float]:
    """Return ``axis`` rotated ``splay_deg`` off-axis at azimuth ``theta`` around ``axis``.

    Builds a local orthonormal frame (``axis``, ``u``, ``v``), then returns
    ``cos(splay)*axis + sin(splay)*(cos(theta)*u + sin(theta)*v)``.
    """
    ax = np.array(axis, dtype=np.float32)
    n = np.linalg.norm(ax)
    if n == 0.0:
        return axis
    ax = ax / n
    # Pick a helper vector not parallel to the axis.
    helper = (
        np.array([0.0, 1.0, 0.0], dtype=np.float32)
        if abs(ax[1]) < 0.9
        else np.array([1.0, 0.0, 0.0], dtype=np.float32)
    )
    u = np.cross(ax, helper)
    un = np.linalg.norm(u)
    if un == 0.0:
        return axis
    u = u / un
    v = np.cross(ax, u)
    splay_rad = math.radians(splay_deg)
    cos_s = math.cos(splay_rad)
    sin_s = math.sin(splay_rad)
    d = cos_s * ax + sin_s * (math.cos(theta) * u + math.sin(theta) * v)
    return (float(d[0]), float(d[1]), float(d[2]))
