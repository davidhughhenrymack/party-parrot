"""Parity checks for moving-head preview math (desktop ↔ web)."""

from __future__ import annotations

import math

import pytest

from parrot.vj.moving_head_visual import (
    aim_group_rotation_z_radians,
    mechanical_tilt_max_deg,
    mechanical_tilt_neutral_deg,
    pan_radians_for_render,
    tilt_radians_for_render,
)


def test_pan_radians_at_logical_zero() -> None:
    assert pan_radians_for_render(0.0) == pytest.approx(math.pi)


def test_aim_group_z_matches_dense_scene_controller() -> None:
    """Web: rotation.z = -degToRad(pan). Desktop +Y pan adds π (fixed mesh/orientation)."""
    for deg in (0.0, 13.7, -40.0, 180.0, 360.0):
        aim_z = -math.radians(deg)
        assert aim_group_rotation_z_radians(deg) == pytest.approx(aim_z)
        assert pan_radians_for_render(deg) == pytest.approx(aim_z + math.pi)


def test_tilt_neutral_logical_value() -> None:
    """Chauvet 270° mechanical tilt is centered on 'head up' at logical 135°."""
    assert mechanical_tilt_neutral_deg() == pytest.approx(135.0)
    assert mechanical_tilt_max_deg() == pytest.approx(270.0)


def test_tilt_at_neutral_points_beam_up_desktop() -> None:
    """tilt_deg = 135° → rotation of -π/2 around +X, which takes local +Z → +Y (world up).

    This is the critical invariant for the desktop moving-head renderer: at DMX
    tilt_coarse = 127 the head must point straight up from the base.
    """
    assert tilt_radians_for_render(135.0) == pytest.approx(-math.pi / 2.0)


def test_tilt_endpoints_symmetric_from_up() -> None:
    """DMX 0/255 → logical 0°/270° → ±135° from up (symmetric, full mechanical sweep)."""
    at_low = tilt_radians_for_render(0.0)
    at_high = tilt_radians_for_render(270.0)
    # Offsets from the "up" position (-π/2) should be equal and opposite.
    assert (at_low - (-math.pi / 2.0)) == pytest.approx(-math.radians(135.0))
    assert (at_high - (-math.pi / 2.0)) == pytest.approx(math.radians(135.0))


def test_tilt_clamped_to_mechanical_range() -> None:
    """Values outside [0, 270] clamp to the mechanical endpoints (no wrap-around)."""
    assert tilt_radians_for_render(-50.0) == pytest.approx(tilt_radians_for_render(0.0))
    assert tilt_radians_for_render(400.0) == pytest.approx(tilt_radians_for_render(270.0))


def test_pan_radians_explicit_formula() -> None:
    for deg in (0.0, 12.5, 90.0):
        assert pan_radians_for_render(deg) == pytest.approx(
            -math.radians(deg) + math.pi
        )
