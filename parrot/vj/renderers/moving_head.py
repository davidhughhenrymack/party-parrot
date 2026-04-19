#!/usr/bin/env python3

from beartype import beartype
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
        pan_rad = pan_radians_for_render(float(self.fixture.get_pan_angle()))
        tilt_rad = tilt_radians_for_render(float(self.fixture.get_tilt_angle()))
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

        # Get 3D position (center of fixture)
        position_3d = self.get_3d_position(canvas_size)

        body_size = self.cube_size * 0.4
        body_color = (0.3, 0.3, 0.3)
        base_height = body_size * 0.42
        moving_body_height = body_size * 0.5
        moving_body_width = body_size * 0.5
        moving_body_depth = body_size * 1.2
        moving_body_y = base_height + moving_body_height / 2 + body_size * 0.3

        moving_body_rotation = self._moving_body_rotation()

        half_depth = moving_body_depth * 0.5
        pivot_local = np.array([0.0, 0.0, half_depth], dtype=np.float32)
        pivot_delta = quaternion_rotate_vector(
            self.orientation,
            pivot_local - quaternion_rotate_vector(moving_body_rotation, pivot_local),
        )
        body_position = (
            position_3d[0] + float(pivot_delta[0]),
            position_3d[1] + float(pivot_delta[1]),
            position_3d[2] + float(pivot_delta[2]),
        )

        # Fixed base at fixture position
        with self.room_renderer.local_position(position_3d):
            with self.room_renderer.local_rotation(self.orientation):
                base_width = body_size * 1.2
                base_depth = body_size * 0.8
                self.room_renderer.render_rectangular_box(
                    0.0,
                    base_height / 2,
                    0.0,
                    body_color,
                    base_width,
                    base_height,
                    base_depth,
                )

                # Neutral-pan indicator: lighter grey slab on the base “front” in
                # `room_3d` box space (face normal −Z; see `render_rectangular_box`).
                # Parrot Cloud’s Z-up base puts the same marker on the −venue-Y face;
                # see `parrot.vj.moving_head_visual` + AGENTS.md. Pan/tilt for mesh/beam
                # use `pan_radians_for_render` / `tilt_radians_for_render` only.
                screen_color = (0.65, 0.65, 0.65)
                screen_thickness = base_depth * 0.08
                screen_width = base_width * 0.55
                screen_height = base_height * 0.55
                self.room_renderer.render_rectangular_box(
                    0.0,
                    base_height / 2,
                    -(base_depth / 2 + screen_thickness / 2),
                    screen_color,
                    screen_width,
                    screen_height,
                    screen_thickness,
                )

        # Moving head: pan/tilt about the rear face of the head cuboid (not its center)
        with self.room_renderer.local_position(body_position):
            with self.room_renderer.local_rotation(self.orientation):
                with self.room_renderer.local_rotation(moving_body_rotation):
                    self.room_renderer.render_rectangular_box(
                        0.0,
                        moving_body_y,
                        0.0,
                        body_color,
                        moving_body_width,
                        moving_body_height,
                        moving_body_depth,
                    )

        # Render DMX address
        self.render_dmx_address(canvas_size)

    def render_emissive(self, context, canvas_size: tuple[float, float], frame: Frame):
        """Render only the emissive parts (bulb and beam)"""
        if self.room_renderer is None:
            return

        position_3d = self.get_3d_position(canvas_size)

        body_size = self.cube_size * 0.4
        base_height = body_size * 0.42
        moving_body_height = body_size * 0.5
        moving_body_depth = body_size * 1.2

        bulb_radius = body_size * 0.3
        bulb_color = self.get_color()
        dimmer = self.get_effective_dimmer(frame)

        moving_body_rotation = self._moving_body_rotation()

        # Beam + bulb render *inside* the moving-body transform stack (see the
        # nested ``local_rotation`` contexts below), so their direction/normal
        # must be expressed in the body's local frame. The body's long axis is
        # +Z locally, so the beam shines straight out of the head along +Z and
        # the room rotation stack carries it to the right world direction.
        beam_direction = (0.0, 0.0, 1.0)

        half_depth = moving_body_depth * 0.5
        pivot_local = np.array([0.0, 0.0, half_depth], dtype=np.float32)
        pivot_delta = quaternion_rotate_vector(
            self.orientation,
            pivot_local - quaternion_rotate_vector(moving_body_rotation, pivot_local),
        )
        body_position = (
            position_3d[0] + float(pivot_delta[0]),
            position_3d[1] + float(pivot_delta[1]),
            position_3d[2] + float(pivot_delta[2]),
        )

        with self.room_renderer.local_position(body_position):
            with self.room_renderer.local_rotation(self.orientation):
                with self.room_renderer.local_rotation(moving_body_rotation):
                    bulb_y = (
                        base_height
                        + moving_body_height / 2
                        + body_size * 0.3
                        + body_size * 0.05
                    )
                    bulb_z = body_size * 0.6

                    brightness_multiplier = 1.0 + dimmer * 2.0
                    boosted_bulb_color = (
                        min(bulb_color[0] * brightness_multiplier, 1.0),
                        min(bulb_color[1] * brightness_multiplier, 1.0),
                        min(bulb_color[2] * brightness_multiplier, 1.0),
                    )

                    capped_alpha = min(dimmer * 1.5, 1.0)

                    self.room_renderer.render_emission_circle(
                        (0.0, bulb_y, bulb_z),
                        boosted_bulb_color,
                        bulb_radius,
                        normal=beam_direction,
                        alpha=capped_alpha,
                    )

                    if dimmer > 0.05:
                        beam_length = 15.0
                        beam_alpha = capped_alpha
                        prism_on, prism_speed = self.fixture.get_prism()
                        # Fixture focus modulates end_radius: tight focus → narrow beam,
                        # wide focus → the original chunky cone. start_radius stays put
                        # since the lens aperture doesn't visibly change with focus.
                        focus_mult = _focus_width_multiplier(float(self.fixture.get_focus()))

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
                                    0.0,
                                    bulb_y,
                                    bulb_z,
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
                                0.0,
                                bulb_y,
                                bulb_z,
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
