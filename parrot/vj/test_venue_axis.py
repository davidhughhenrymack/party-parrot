"""Tests for venue(Z-up) ↔ desktop(Y-up) rotation conversion.

These tests pin the invariants described in AGENTS.md "Venue ↔ desktop
axis mapping". The desktop housing must orient the same way the web
preview does for any stored `rotation_x/y/z`.
"""

import math

import numpy as np
import pytest

from parrot.vj.renderers.base import quaternion_rotate_vector
from parrot.vj.venue_axis import venue_rotation_to_desktop_quaternion


def _rotate(q: np.ndarray, v: tuple[float, float, float]) -> np.ndarray:
    return quaternion_rotate_vector(q, np.array(v, dtype=np.float32))


def _assert_vec_close(
    actual: np.ndarray, expected: tuple[float, float, float], tol: float = 1e-5
) -> None:
    assert actual[0] == pytest.approx(expected[0], abs=tol)
    assert actual[1] == pytest.approx(expected[1], abs=tol)
    assert actual[2] == pytest.approx(expected[2], abs=tol)


def test_identity_is_identity():
    q = venue_rotation_to_desktop_quaternion(0.0, 0.0, 0.0)
    _assert_vec_close(_rotate(q, (1.0, 0.0, 0.0)), (1.0, 0.0, 0.0))
    _assert_vec_close(_rotate(q, (0.0, 1.0, 0.0)), (0.0, 1.0, 0.0))
    _assert_vec_close(_rotate(q, (0.0, 0.0, 1.0)), (0.0, 0.0, 1.0))


def test_rotation_z_leaves_desktop_up_axis_invariant():
    """Rotation around venue Z (height) must be a pure yaw in desktop space.

    Desktop Y is the up axis, so a Z-rotation must not move (0, 1, 0).
    """
    q = venue_rotation_to_desktop_quaternion(0.0, 0.0, math.pi / 3)
    _assert_vec_close(_rotate(q, (0.0, 1.0, 0.0)), (0.0, 1.0, 0.0))


def test_rotation_y_leaves_desktop_depth_axis_invariant():
    """Rotation around venue Y (depth) must not move desktop Z (depth)."""
    q = venue_rotation_to_desktop_quaternion(0.0, math.pi / 4, 0.0)
    _assert_vec_close(_rotate(q, (0.0, 0.0, 1.0)), (0.0, 0.0, 1.0))


def test_rotation_x_leaves_desktop_x_axis_invariant():
    q = venue_rotation_to_desktop_quaternion(math.pi / 5, 0.0, 0.0)
    _assert_vec_close(_rotate(q, (1.0, 0.0, 0.0)), (1.0, 0.0, 0.0))


def test_yaw_rotates_upstage_into_the_xz_plane_consistently_with_web():
    """A fixture facing upstage is `-venue_y` (= `-desktop_z`). Under a
    venue-Z yaw of `rz`, its forward vector should sweep through the
    desktop X axis the same way Three.js's `group.rotation.z = rz` does
    in the web scene. This pins the sign of the rotation (no accidental
    inversion between the two renderers).
    """
    rz = math.pi / 2
    q = venue_rotation_to_desktop_quaternion(0.0, 0.0, rz)
    rotated = _rotate(q, (0.0, 0.0, -1.0))
    # Rotating −desktop_Z by +rz around desktop_Y (right-hand rule):
    # `R_y(θ)·(0, 0, −1) = (−sin θ, 0, −cos θ)`.
    _assert_vec_close(rotated, (-math.sin(rz), 0.0, -math.cos(rz)))


def test_matches_threejs_intrinsic_xyz_for_pure_axes():
    """For a single-axis rotation the quaternion should equal a textbook
    axis-angle quaternion around the remapped desktop axis.
    """
    half = math.pi / 8
    c, s = math.cos(half), math.sin(half)

    qz = venue_rotation_to_desktop_quaternion(0.0, 0.0, math.pi / 4)
    np.testing.assert_allclose(qz, np.array([0.0, s, 0.0, c]), atol=1e-6)

    qy = venue_rotation_to_desktop_quaternion(0.0, math.pi / 4, 0.0)
    np.testing.assert_allclose(qy, np.array([0.0, 0.0, s, c]), atol=1e-6)

    qx = venue_rotation_to_desktop_quaternion(math.pi / 4, 0.0, 0.0)
    np.testing.assert_allclose(qx, np.array([s, 0.0, 0.0, c]), atol=1e-6)


def test_intrinsic_xyz_composition_matches_threejs():
    """Composed rotation must equal Three.js `Matrix4.makeRotationFromEuler(...,
    'XYZ')`: M = Rx(rx) * Ry(ry) * Rz(rz) on column vectors, with each R
    using the remapped desktop axis.
    """
    rx, ry, rz = 0.3, -0.5, 0.7
    q = venue_rotation_to_desktop_quaternion(rx, ry, rz)

    def rot_matrix_x(a: float) -> np.ndarray:
        c, s = math.cos(a), math.sin(a)
        return np.array([[1, 0, 0], [0, c, -s], [0, s, c]], dtype=np.float64)

    def rot_matrix_y(a: float) -> np.ndarray:
        c, s = math.cos(a), math.sin(a)
        return np.array([[c, 0, s], [0, 1, 0], [-s, 0, c]], dtype=np.float64)

    def rot_matrix_z(a: float) -> np.ndarray:
        c, s = math.cos(a), math.sin(a)
        return np.array([[c, -s, 0], [s, c, 0], [0, 0, 1]], dtype=np.float64)

    # Three.js intrinsic XYZ = Rx_desktop * Ry_desktop * Rz_desktop with
    # each rotation around the *desktop* axis that the corresponding venue
    # axis maps to (X→X, Y→Z, Z→Y).
    expected = rot_matrix_x(rx) @ rot_matrix_z(ry) @ rot_matrix_y(rz)

    for probe in [(1.0, 0.0, 0.0), (0.0, 1.0, 0.0), (0.0, 0.0, 1.0), (1.0, 2.0, 3.0)]:
        got = _rotate(q, probe)
        want = expected @ np.array(probe, dtype=np.float64)
        np.testing.assert_allclose(got, want, atol=1e-5)
