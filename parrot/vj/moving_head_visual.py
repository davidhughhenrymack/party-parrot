"""
Moving-head *preview* math shared by the OpenGL room renderer and the web venue editor.

This is intentionally small and explicit: lighting designers must see the same pan/tilt
and the same “neutral pan” base marking in Party Parrot (desktop) and Parrot Cloud (web).

The functions here are the single source of truth for how logical DMX angles
(`MovingHead.pan_angle` / `tilt_angle`, surfaced as `pan_deg` / `tilt_deg` in runtime JSON)
map to the renderer’s internal radians. They must stay in lockstep with
`parrot_cloud/frontend/src/movingHeadPreviewMath.js`.

Scaling (0.5×) matches historical VJ preview behavior: the mesh is not a 1:1 mechanical
CAD model, but the motion must stay consistent everywhere.
"""

from __future__ import annotations

import math

from beartype import beartype

# Same cap as `parrot/vj/renderers/moving_head.py` had inline — tilts beyond ~180° are rare;
# clamping avoids the proxy head folding through the floor in preview.
_MECHANICAL_TILT_MAX_DEG = 200.0


@beartype
def pan_radians_for_render(pan_deg: float) -> float:
    """Radians for yoke pan in the desktop moving-head renderer (around room +Y).

    Includes a fixed +π offset so “logical pan = 0°” still aims the proxy usefully;
    web applies the equivalent as ``aimGroup.rotation.z = -(pan_radians_for_render(pan) - π)``.
    """
    return math.radians(float(pan_deg)) * 0.5 + math.pi


@beartype
def tilt_radians_for_render(tilt_deg: float) -> float:
    """Radians for head tilt after clamping to a believable mechanical sweep."""
    td = max(0.0, min(float(tilt_deg), _MECHANICAL_TILT_MAX_DEG))
    return math.radians(td) * 0.5


@beartype
def aim_group_rotation_z_radians(pan_deg: float) -> float:
    """Pan rotation for the web venue editor’s Z-up ``aimGroup`` (see `movingHeadPreviewMath.js`)."""
    return -(pan_radians_for_render(pan_deg) - math.pi)


@beartype
def mechanical_tilt_max_deg() -> float:
    return _MECHANICAL_TILT_MAX_DEG
