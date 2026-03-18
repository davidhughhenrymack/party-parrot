import os
import tempfile

import numpy as np
import pytest

from parrot.fixtures.position_manager import FixturePositionManager
from parrot.patch_bay import (
    add_custom_venue,
    add_fixture_to_venue,
    get_all_venues,
    reload_patch_bay_configuration,
    resolve_venue,
    venue_patches,
    venues,
)
from parrot.state import State
from parrot.venue_editor import SelectionTarget, VenueEditorController
from parrot.vj.renderers.room_3d import Room3DRenderer


@pytest.fixture
def temp_workspace():
    original_cwd = os.getcwd()
    temp_dir = tempfile.mkdtemp()
    os.chdir(temp_dir)
    reload_patch_bay_configuration()
    yield temp_dir
    os.chdir(original_cwd)
    reload_patch_bay_configuration()

    import shutil

    shutil.rmtree(temp_dir)


def test_can_add_custom_venue_and_fixture(temp_workspace):
    custom_venue = add_custom_venue("Warehouse Alpha")

    assert resolve_venue("warehouse_alpha") == custom_venue
    assert custom_venue in get_all_venues()
    assert venue_patches[custom_venue] == []

    new_fixture = add_fixture_to_venue(custom_venue, "ParRGB", 55)

    assert new_fixture.address == 55
    assert len(venue_patches[custom_venue]) == 1


def test_position_manager_persists_floor_size_and_video_wall(temp_workspace):
    state = State()
    state.set_venue(venues.dmack)
    position_manager = FixturePositionManager(state)

    position_manager.set_floor_size_feet(24.0)
    position_manager.set_video_wall_config(
        {"x": 1.5, "y": 4.0, "z": -3.25, "width": 8.0, "height": 5.0}
    )

    reloaded_manager = FixturePositionManager(state)
    reloaded_video_wall = reloaded_manager.get_video_wall_config()

    assert reloaded_manager.get_floor_size_feet() == pytest.approx(24.0)
    assert reloaded_video_wall["x"] == pytest.approx(1.5)
    assert reloaded_video_wall["y"] == pytest.approx(4.0)
    assert reloaded_video_wall["z"] == pytest.approx(-3.25)
    assert reloaded_video_wall["width"] == pytest.approx(8.0)
    assert reloaded_video_wall["height"] == pytest.approx(5.0)


class FakeRoomRenderer:
    def project_world_to_screen(self, position):
        return (position[0] * 100.0, position[1] * 100.0)

    def convert_3d_to_2d(self, room_x, room_y, room_z):
        return (room_x, room_z, room_y)

    def set_floor_size_feet(self, floor_size_feet):
        self.floor_size_feet = floor_size_feet

    def render_axis_gizmo(self, *args, **kwargs):
        return None


class FakeFixtureRenderer:
    def __init__(self, fixture):
        self.fixture = fixture
        self.position = (10.0, 20.0, 3.0)
        self.orientation = np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32)

    def set_position(self, x, y, z):
        self.position = (x, y, z)

    def get_3d_position(self, canvas_size):
        return (self.position[0], self.position[2], self.position[1])


def test_editor_moves_and_rotates_selected_fixture(temp_workspace):
    state = State()
    state.set_show_fixture_mode(True)
    state.set_venue(venues.dmack)
    position_manager = FixturePositionManager(state)

    fixture = venue_patches[venues.dmack][0]
    renderer = FakeFixtureRenderer(fixture)
    position_manager.set_fixture_position(fixture, *renderer.position)
    position_manager.set_fixture_orientation(
        fixture, np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32)
    )

    editor = VenueEditorController(state, position_manager)
    editor.update_scene(
        FakeRoomRenderer(),
        [renderer],
        (500.0, 500.0),
        position_manager.get_video_wall_config(),
    )
    editor.selected_target = SelectionTarget(kind="fixture", fixture_id=fixture.id)

    editor._move_selected("x", 2.0)

    assert renderer.position[0] == pytest.approx(12.0)
    assert position_manager.get_fixture_position(fixture)[0] == pytest.approx(12.0)

    editor._rotate_selected("y", 1)

    assert not np.allclose(
        position_manager.get_fixture_orientation(fixture),
        np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32),
    )


def test_floor_size_coordinate_conversion_round_trips():
    room_renderer = Room3DRenderer.__new__(Room3DRenderer)
    room_renderer.floor_size_feet = 24.0

    room_x, room_y, room_z = Room3DRenderer.convert_2d_to_3d(
        room_renderer, 500.0, 500.0, 3.0, 500.0, 500.0
    )
    canvas_x, canvas_y, height = Room3DRenderer.convert_3d_to_2d(
        room_renderer, room_x, room_y, room_z
    )

    assert room_x == pytest.approx(12.0)
    assert room_z == pytest.approx(12.0)
    assert canvas_x == pytest.approx(500.0)
    assert canvas_y == pytest.approx(500.0)
    assert height == pytest.approx(3.0)
