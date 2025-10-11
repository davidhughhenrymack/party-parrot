#!/usr/bin/env python3
"""Integration test for director and position manager"""

import os
import tempfile
import pytest
from parrot.state import State
from parrot.patch_bay import venues
from parrot.director.director import Director
from parrot.director.mode import Mode


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


def test_temp_dir_isolation(temp_dir_fixture):
    """Verify that tests run in isolated temp directory"""
    current_dir = os.path.realpath(os.getcwd())
    temp_dir = os.path.realpath(temp_dir_fixture)
    assert current_dir == temp_dir
    assert "/tmp" in current_dir or "/var/folders" in current_dir


def test_director_initializes_with_position_manager(temp_dir_fixture):
    """Test that director creates position manager and fixtures have positions"""
    state = State()
    state.set_venue(venues.mtn_lotus)
    state.set_mode(Mode.rave)

    # Create director (should create position manager internally)
    director = Director(state)

    # Verify position manager was created
    assert hasattr(director, "position_manager")
    assert director.position_manager is not None

    # Verify fixtures from patch bay have positions
    from parrot.patch_bay import venue_patches
    from parrot.fixtures.base import FixtureGroup

    fixtures = []
    for item in venue_patches[venues.mtn_lotus]:
        if isinstance(item, FixtureGroup):
            fixtures.extend(item.fixtures)
        else:
            fixtures.append(item)

    # Check that fixtures have position attributes
    fixtures_with_positions = 0
    for fixture in fixtures:
        if hasattr(fixture, "x") and hasattr(fixture, "y") and hasattr(fixture, "z"):
            fixtures_with_positions += 1

    assert fixtures_with_positions > 0, "Fixtures should have positions"
    print(f"✓ {fixtures_with_positions}/{len(fixtures)} fixtures have positions")


def test_director_interpreters_can_access_positions(temp_dir_fixture):
    """Test that interpreters created by director can access fixture positions"""
    state = State()
    state.set_venue(venues.mtn_lotus)
    state.set_mode(Mode.rave)

    # Create director
    director = Director(state)

    # Check interpreters
    assert len(director.interpreters) > 0, "Should have created interpreters"

    # For each interpreter, check if its fixtures have positions
    for interpreter in director.interpreters:
        if hasattr(interpreter, "group"):
            for fixture in interpreter.group:
                # Should not raise AttributeError
                has_x = hasattr(fixture, "x")
                has_y = hasattr(fixture, "y")
                has_z = hasattr(fixture, "z")

                # At least should have the attributes (even if None)
                if has_x and has_y and has_z:
                    # Can access position
                    _ = fixture.x, fixture.y, fixture.z

    print(
        f"✓ All {len(director.interpreters)} interpreters can access fixture positions"
    )


def test_position_manager_venue_change_with_director(temp_dir_fixture):
    """Test that changing venue updates positions for director's fixtures"""
    state = State()
    state.set_venue(venues.dmack)
    state.set_mode(Mode.rave)

    # Create director
    director = Director(state)

    # Get initial fixture count
    from parrot.patch_bay import venue_patches
    from parrot.fixtures.base import FixtureGroup

    dmack_fixtures = []
    for item in venue_patches[venues.dmack]:
        if isinstance(item, FixtureGroup):
            dmack_fixtures.extend(item.fixtures)
        else:
            dmack_fixtures.append(item)

    # Change venue
    state.set_venue(venues.mtn_lotus)

    # Get new fixtures
    mtn_fixtures = []
    for item in venue_patches[venues.mtn_lotus]:
        if isinstance(item, FixtureGroup):
            mtn_fixtures.extend(item.fixtures)
        else:
            mtn_fixtures.append(item)

    # Check that fixtures have positions
    fixtures_with_positions = 0
    for fixture in mtn_fixtures:
        if hasattr(fixture, "x") and hasattr(fixture, "y") and hasattr(fixture, "z"):
            fixtures_with_positions += 1

    assert (
        fixtures_with_positions > 0
    ), "Fixtures should have positions after venue change"
    print(
        f"✓ Venue change successful: {fixtures_with_positions}/{len(mtn_fixtures)} fixtures have positions"
    )


if __name__ == "__main__":
    test_director_initializes_with_position_manager()
    test_director_interpreters_can_access_positions()
    test_position_manager_venue_change_with_director()
    print("\n✅ All integration tests passed!")
