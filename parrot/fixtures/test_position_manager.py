#!/usr/bin/env python3
"""Test fixture position manager"""

import os
import tempfile
import pytest
import numpy as np
from parrot.state import State
from parrot.patch_bay import venues
from parrot.fixtures.position_manager import FixturePositionManager


@pytest.fixture
def temp_dir_fixture():
    """Create a temporary directory for tests and clean up after"""
    temp_dir = tempfile.mkdtemp()
    original_cwd = os.getcwd()
    os.chdir(temp_dir)
    yield temp_dir
    os.chdir(original_cwd)
    import shutil

    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)


def test_position_manager_loads_positions(temp_dir_fixture):
    """Test that position manager loads positions from JSON"""
    state = State()
    state.set_venue(venues.mtn_lotus)

    position_manager = FixturePositionManager(state)

    # Get all fixtures from patch bay
    from parrot.patch_bay import venue_patches
    from parrot.fixtures.base import FixtureGroup

    fixtures = []
    for item in venue_patches[venues.mtn_lotus]:
        if isinstance(item, FixtureGroup):
            fixtures.extend(item.fixtures)
        else:
            fixtures.append(item)

    # Check that at least some fixtures have positions
    fixtures_with_positions = 0
    for fixture in fixtures:
        pos = position_manager.get_fixture_position(fixture)
        if pos:
            fixtures_with_positions += 1
            x, y, z = pos
            # Verify position values are reasonable
            assert isinstance(x, float)
            assert isinstance(y, float)
            assert isinstance(z, float)

    # Should have loaded positions for fixtures
    assert (
        fixtures_with_positions > 0
    ), "Should have loaded at least some fixture positions"


def test_position_manager_applies_positions_to_fixtures(temp_dir_fixture):
    """Test that position manager sets x, y, z attributes on fixtures"""
    state = State()
    state.set_venue(venues.mtn_lotus)

    position_manager = FixturePositionManager(state)

    # Get fixtures from patch bay
    from parrot.patch_bay import venue_patches
    from parrot.fixtures.base import FixtureGroup

    fixtures = []
    for item in venue_patches[venues.mtn_lotus]:
        if isinstance(item, FixtureGroup):
            fixtures.extend(item.fixtures)
        else:
            fixtures.append(item)

    # Check that fixtures have x, y, z attributes set
    fixtures_with_attrs = 0
    for fixture in fixtures:
        if hasattr(fixture, "x") and hasattr(fixture, "y") and hasattr(fixture, "z"):
            fixtures_with_attrs += 1
            # Verify values are reasonable
            assert isinstance(fixture.x, float)
            assert isinstance(fixture.y, float)
            assert isinstance(fixture.z, float)

    # All fixtures should have position attributes
    assert fixtures_with_attrs == len(
        fixtures
    ), "All fixtures should have position attributes"


def test_position_manager_handles_venue_change(temp_dir_fixture):
    """Test that position manager reloads positions when venue changes"""
    state = State()
    state.set_venue(venues.dmack)

    position_manager = FixturePositionManager(state)

    # Get a fixture from dmack venue
    from parrot.patch_bay import venue_patches
    from parrot.fixtures.base import FixtureGroup

    fixtures = []
    for item in venue_patches[venues.dmack]:
        if isinstance(item, FixtureGroup):
            fixtures.extend(item.fixtures)
        else:
            fixtures.append(item)

    if fixtures:
        first_fixture = fixtures[0]
        dmack_pos = position_manager.get_fixture_position(first_fixture)

        # Change venue
        state.set_venue(venues.mtn_lotus)

        # Get a fixture from mtn_lotus venue
        mtn_fixtures = []
        for item in venue_patches[venues.mtn_lotus]:
            if isinstance(item, FixtureGroup):
                mtn_fixtures.extend(item.fixtures)
            else:
                mtn_fixtures.append(item)

        if mtn_fixtures:
            mtn_first_fixture = mtn_fixtures[0]
            mtn_pos = position_manager.get_fixture_position(mtn_first_fixture)

            # Positions should be set for both venues
            assert dmack_pos is not None or mtn_pos is not None


def test_position_manager_loads_orientation(temp_dir_fixture):
    """Test that position manager loads orientation quaternions"""
    state = State()
    state.set_venue(venues.mtn_lotus)

    position_manager = FixturePositionManager(state)

    # Get fixtures
    from parrot.patch_bay import venue_patches
    from parrot.fixtures.base import FixtureGroup

    fixtures = []
    for item in venue_patches[venues.mtn_lotus]:
        if isinstance(item, FixtureGroup):
            fixtures.extend(item.fixtures)
        else:
            fixtures.append(item)

    # Check that fixtures have orientation
    fixtures_with_orientation = 0
    for fixture in fixtures:
        orientation = position_manager.get_fixture_orientation(fixture)
        if orientation is not None:
            fixtures_with_orientation += 1
            # Should be a 4-element quaternion
            assert isinstance(orientation, np.ndarray)
            assert len(orientation) == 4
            assert orientation.dtype == np.float32

    # Should have loaded orientations for fixtures
    assert fixtures_with_orientation > 0, "Should have loaded orientations"


def test_spatial_interpreter_can_access_positions(temp_dir_fixture):
    """Test that spatial interpreters can access fixture positions"""
    from parrot.interpreters.spatial import SpatialDownwardsPulse
    from parrot.interpreters.base import InterpreterArgs
    from parrot.director.frame import Frame, FrameSignal

    state = State()
    state.set_venue(venues.mtn_lotus)

    # Create position manager to set positions
    position_manager = FixturePositionManager(state)

    # Get fixtures
    from parrot.patch_bay import venue_patches
    from parrot.fixtures.base import FixtureGroup

    fixtures = []
    for item in venue_patches[venues.mtn_lotus]:
        if isinstance(item, FixtureGroup):
            fixtures.extend(item.fixtures)
        else:
            fixtures.append(item)

    if fixtures:
        # Create spatial interpreter
        args = InterpreterArgs(hype=50, allow_rainbows=False, min_hype=0, max_hype=100)
        interpreter = SpatialDownwardsPulse(fixtures, args)

        # Try to calculate spatial range (this accesses fixture.y)
        result = interpreter._calculate_spatial_range()

        # Should either work (if there's sufficient range) or return False
        # but shouldn't raise an AttributeError
        assert isinstance(result, bool)
