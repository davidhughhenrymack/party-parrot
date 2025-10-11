#!/usr/bin/env python3

import pytest
from beartype import beartype
from unittest.mock import Mock

from parrot.fixtures.motionstrip import Motionstrip38, MotionstripBulb
from parrot.vj.renderers.motionstrip import MotionstripRenderer


@beartype
class TestMotionstripRenderer:
    """Test suite for MotionstripRenderer pan rotation"""

    def test_pan_rotation_at_zero(self):
        """Pan value 0 should result in -90 degree rotation"""
        fixture = Motionstrip38(patch=1, pan_lower=0, pan_upper=255, invert_pan=False)
        fixture.set_pan(0)
        renderer = MotionstripRenderer(fixture, room_renderer=None)

        pan_rotation = renderer._get_pan_rotation()
        assert pan_rotation == pytest.approx(-90.0, abs=0.1)

    def test_pan_rotation_at_max(self):
        """Pan value 255 should result in +90 degree rotation"""
        fixture = Motionstrip38(patch=1, pan_lower=0, pan_upper=255, invert_pan=False)
        fixture.set_pan(255)
        renderer = MotionstripRenderer(fixture, room_renderer=None)

        pan_rotation = renderer._get_pan_rotation()
        assert pan_rotation == pytest.approx(90.0, abs=0.1)

    def test_pan_rotation_at_center(self):
        """Pan value 127.5 should result in 0 degree rotation (centered)"""
        fixture = Motionstrip38(patch=1, pan_lower=0, pan_upper=255, invert_pan=False)
        fixture.set_pan(127.5)
        renderer = MotionstripRenderer(fixture, room_renderer=None)

        pan_rotation = renderer._get_pan_rotation()
        assert pan_rotation == pytest.approx(0.0, abs=0.5)

    def test_pan_rotation_with_invert(self):
        """Invert_pan should flip the rotation direction through fixture's set_pan logic"""
        # Normal pan at 200
        fixture_normal = Motionstrip38(
            patch=1, pan_lower=0, pan_upper=255, invert_pan=False
        )
        fixture_normal.set_pan(200)
        renderer_normal = MotionstripRenderer(fixture_normal, room_renderer=None)
        rotation_normal = renderer_normal._get_pan_rotation()

        # Inverted pan at 200 - the fixture's set_pan inverts it to (255-200)=55
        # So it should produce the same rotation as set_pan(55) on a normal fixture
        fixture_inverted = Motionstrip38(
            patch=1, pan_lower=0, pan_upper=255, invert_pan=True
        )
        fixture_inverted.set_pan(200)
        renderer_inverted = MotionstripRenderer(fixture_inverted, room_renderer=None)
        rotation_inverted = renderer_inverted._get_pan_rotation()

        # Verify inverted fixture at 200 produces same result as normal fixture at 55
        fixture_check = Motionstrip38(
            patch=1, pan_lower=0, pan_upper=255, invert_pan=False
        )
        fixture_check.set_pan(55)
        renderer_check = MotionstripRenderer(fixture_check, room_renderer=None)
        rotation_check = renderer_check._get_pan_rotation()

        assert rotation_inverted == pytest.approx(rotation_check, abs=0.1)

        # And it should be on the opposite side from normal rotation
        assert rotation_inverted < 0 and rotation_normal > 0

    def test_pan_rotation_with_custom_range(self):
        """Pan rotation should work with custom pan ranges"""
        fixture = Motionstrip38(patch=1, pan_lower=100, pan_upper=200, invert_pan=False)

        # Set pan to minimum of range
        fixture.set_pan(0)
        renderer = MotionstripRenderer(fixture, room_renderer=None)
        assert renderer._get_pan_rotation() == pytest.approx(-90.0, abs=0.1)

        # Set pan to maximum of range
        fixture.set_pan(255)
        renderer = MotionstripRenderer(fixture, room_renderer=None)
        assert renderer._get_pan_rotation() == pytest.approx(90.0, abs=0.1)

        # Set pan to center of range
        fixture.set_pan(127.5)
        renderer = MotionstripRenderer(fixture, room_renderer=None)
        assert renderer._get_pan_rotation() == pytest.approx(0.0, abs=0.5)
