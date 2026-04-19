"""Parity checks for moving-head preview math (desktop ↔ web)."""

from __future__ import annotations

import math

import pytest

from parrot.vj.moving_head_visual import (
    aim_group_rotation_z_radians,
    pan_radians_for_render,
    tilt_radians_for_render,
)


def test_pan_radians_at_logical_zero() -> None:
    assert pan_radians_for_render(0.0) == pytest.approx(math.pi)


def test_aim_group_z_is_half_negative_pan_without_pi() -> None:
    """Web Euler cancels the desktop +π offset: rotation.z = −0.5×rad(pan)."""
    for deg in (0.0, 13.7, -40.0, 180.0):
        expected = -math.radians(deg) * 0.5
        assert aim_group_rotation_z_radians(deg) == pytest.approx(expected)


def test_tilt_clamped_and_scaled() -> None:
    assert tilt_radians_for_render(0.0) == 0.0
    assert tilt_radians_for_render(400.0) == pytest.approx(math.radians(200.0) * 0.5)


def test_pan_radians_explicit_formula() -> None:
    for deg in (0.0, 12.5, 90.0):
        assert pan_radians_for_render(deg) == pytest.approx(
            math.radians(deg) * 0.5 + math.pi
        )
