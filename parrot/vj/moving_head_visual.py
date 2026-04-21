"""
Moving-head *preview* math shared by the OpenGL room renderer and the web venue editor.

This is intentionally small and explicit: lighting designers must see the same pan/tilt
and the same “neutral pan” base marking in Party Parrot (desktop) and Parrot Cloud (web).

The functions here are the single source of truth for how logical DMX angles
(`MovingHead.pan_angle` / `tilt_angle`, surfaced as `pan_deg` / `tilt_deg` in runtime JSON)
map to the renderer’s internal radians. They must stay in lockstep with
`parrot_cloud/frontend/src/movingHeadPreviewMath.js` and with
`DenseSceneController.js`, which sets ``aimGroup.rotation.z = -degToRad(pan_deg)``.
"""

from __future__ import annotations

import math

from beartype import beartype

# Chauvet-style moving heads have a 270° mechanical tilt sweep. The logical
# `MovingHead.tilt_angle` (set by `ChauvetMoverBase.set_tilt`) is expressed in
# that unsigned 0..270° space, where the mechanical *center* (=135°) is
# "head pointing straight up from the base". DMX 0 / 255 correspond to the
# two mechanical end-stops, i.e. -135° / +135° from that up-neutral position.
_MECHANICAL_TILT_MAX_DEG = 270.0
_MECHANICAL_TILT_NEUTRAL_DEG = 135.0


@beartype
def pan_radians_for_render(pan_deg: float) -> float:
    """Radians for yoke pan in the desktop moving-head renderer (around room +Y).

    Web uses ``aimGroup.rotation.z = -degToRad(pan_deg)`` (see
    ``aim_group_rotation_z_radians``). The OpenGL mesh/beam forward in ``+Z`` lines up
    with that aim after a fixed ``+π`` around ``+Y`` (same incremental pan as web,
    absolute aim aligned).
    """
    return -math.radians(float(pan_deg)) + math.pi


@beartype
def tilt_radians_for_render(tilt_deg: float) -> float:
    """Radians for head tilt in the desktop renderer (rotation around +X axis).

    The head's local forward in `parrot/vj/renderers/moving_head.py` is +Z, and
    the world "up" is +Y. Rotating +Z by -π/2 around +X gives +Y, so we want
    ``tilt_rad = -π/2`` at the mechanical center (tilt_deg = 135°). The full
    mechanical sweep (0°..270°) therefore maps to tilt_rad in
    ``[-π/2 - 135°, -π/2 + 135°]`` — symmetric ±135° around straight up.
    """
    td = max(0.0, min(float(tilt_deg), _MECHANICAL_TILT_MAX_DEG))
    return math.radians(td - _MECHANICAL_TILT_NEUTRAL_DEG) - math.pi / 2.0


@beartype
def aim_group_rotation_z_radians(pan_deg: float) -> float:
    """Pan rotation for the web venue’s Z-up ``aimGroup`` (``DenseSceneController``)."""
    return -math.radians(float(pan_deg))


@beartype
def mechanical_tilt_max_deg() -> float:
    return _MECHANICAL_TILT_MAX_DEG


@beartype
def mechanical_tilt_neutral_deg() -> float:
    """Logical tilt value (in `MovingHead.tilt_angle` space) meaning 'head straight up'."""
    return _MECHANICAL_TILT_NEUTRAL_DEG
