"""Golden source for venue ↔ desktop coordinate conversions.

The venue DB / venue editor / web 3D preview all agree on a right-handed,
**Z-up** coordinate system:

    venue x: audience-left (−) to audience-right (+)
    venue y: downstage / audience (+) to upstage / DJ (−)
    venue z: height above the floor (+)

The desktop OpenGL renderer uses a right-handed, **Y-up** coordinate
system whose axes line up with venue space as follows:

    desktop X  ≡  venue X  (audience left ↔ right)
    desktop Y  ≡  venue Z  (height)
    desktop Z  ≡  venue Y  (stage depth)

Positions are already remapped in
``parrot/vj/renderers/room_3d.Room3DRenderer.convert_2d_to_3d``. Rotations
stored in the DB as ``rotation_x/y/z`` are Euler angles around the **venue**
axes composed in intrinsic ``'XYZ'`` order (the Three.js default). To make
the desktop housing orient identically to the web preview, the rotation
must be rebuilt around the *desktop* axes that correspond to each venue
axis, keeping the same intrinsic ``XYZ`` composition.

This module is the single source of truth for that conversion. See
``AGENTS.md`` ("Venue ↔ desktop axis mapping") and the call sites in
``parrot_cloud/fixture_catalog.py`` and
``parrot/vj/renderers/room_3d.py``.
"""

from __future__ import annotations

import numpy as np
from beartype import beartype

from parrot.vj.renderers.base import (
    quaternion_from_axis_angle,
    quaternion_multiply,
)


_DESKTOP_AXIS_FOR_VENUE_X = np.array([1.0, 0.0, 0.0], dtype=np.float32)
_DESKTOP_AXIS_FOR_VENUE_Y = np.array([0.0, 0.0, 1.0], dtype=np.float32)
_DESKTOP_AXIS_FOR_VENUE_Z = np.array([0.0, 1.0, 0.0], dtype=np.float32)


@beartype
def venue_rotation_to_desktop_quaternion(
    rotation_x: float, rotation_y: float, rotation_z: float
) -> np.ndarray:
    """Convert stored venue Euler angles to a desktop-space quaternion.

    Inputs are Euler angles around the **venue** axes with intrinsic
    ``'XYZ'`` composition (Three.js default — first rotate around local
    X, then around the new local Y, then around the new local Z).

    The returned quaternion rotates vectors in the desktop renderer's
    Y-up room space so the fixture housing orients identically to the web
    preview.
    """
    qx = quaternion_from_axis_angle(_DESKTOP_AXIS_FOR_VENUE_X, rotation_x)
    qy = quaternion_from_axis_angle(_DESKTOP_AXIS_FOR_VENUE_Y, rotation_y)
    qz = quaternion_from_axis_angle(_DESKTOP_AXIS_FOR_VENUE_Z, rotation_z)
    # Intrinsic XYZ: v_world = Rx * Ry * Rz * v_local (column-vector
    # convention), matching Three.js
    # `Matrix4.makeRotationFromEuler(new Euler(x, y, z, 'XYZ'))`.
    return quaternion_multiply(qx, quaternion_multiply(qy, qz))
