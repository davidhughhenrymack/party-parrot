from dataclasses import dataclass

import numpy as np
from beartype import beartype
from beartype.typing import Any, Callable, Literal, Optional

from parrot.fixtures.position_manager import FixturePositionManager
from parrot.patch_bay import (
    add_custom_venue,
    add_fixture_to_venue,
    get_venue_display_name,
)
from parrot.state import State
from parrot.utils.input_events import InputEvents
from parrot.vj.renderers.base import quaternion_from_axis_angle, quaternion_multiply

EditorMode = Literal["select", "move", "rotate"]


@beartype
@dataclass
class SelectionTarget:
    kind: Literal["fixture", "video_wall"]
    fixture_id: Optional[str] = None


@beartype
class VenueEditorController:
    def __init__(self, state: State, position_manager: FixturePositionManager):
        self.state = state
        self.position_manager = position_manager
        self.mode: EditorMode = "select"
        self.selected_target: Optional[SelectionTarget] = None
        self.room_renderer: Any | None = None
        self.renderers: list[Any] = []
        self.canvas_size = (1200.0, 1200.0)
        self.video_wall_config: dict[str, float] = (
            self.position_manager.get_video_wall_config()
        )
        self.patch_change_callback: Optional[Callable[[], None]] = None
        self.active_drag_axis: Optional[str] = None
        self.layout_dirty = False
        self.gizmo_axis_length = 1.0
        self.selection_threshold_px = 28.0

        input_events = InputEvents.get_instance()
        input_events.register_mouse_press_callback(self._on_mouse_press)
        input_events.register_mouse_drag_callback(self._on_mouse_drag)
        input_events.register_mouse_release_callback(self._on_mouse_release)

    def set_patch_change_callback(self, callback: Callable[[], None]) -> None:
        self.patch_change_callback = callback

    def set_mode(self, mode: EditorMode) -> None:
        self.mode = mode
        self.active_drag_axis = None

    def update_scene(
        self,
        room_renderer: Any,
        renderers: list[Any],
        canvas_size: tuple[float, float],
        video_wall_config: dict[str, float],
    ) -> None:
        self.room_renderer = room_renderer
        self.renderers = renderers
        self.canvas_size = canvas_size
        self.video_wall_config = dict(video_wall_config)

    def get_mode(self) -> EditorMode:
        return self.mode

    def get_selected_label(self) -> str:
        if self.selected_target is None:
            return "None"
        if self.selected_target.kind == "video_wall":
            return "Video Wall"
        renderer = self._get_selected_renderer()
        if renderer is None:
            return "None"
        return f"{renderer.fixture.name} @ {renderer.fixture.address}"

    def get_selection_options(self) -> list[tuple[str, str]]:
        options: list[tuple[str, str]] = [("__none__", "None"), ("__video_wall__", "Video Wall")]
        for renderer in self.renderers:
            options.append(
                (
                    renderer.fixture.id,
                    f"{renderer.fixture.name} @ {renderer.fixture.address}",
                )
            )
        return options

    def get_selected_key(self) -> str:
        if self.selected_target is None:
            return "__none__"
        if self.selected_target.kind == "video_wall":
            return "__video_wall__"
        return self.selected_target.fixture_id or "__none__"

    def select_target_by_key(self, key: str) -> None:
        if key == "__none__":
            self.selected_target = None
            self.active_drag_axis = None
            return
        if key == "__video_wall__":
            self.selected_target = SelectionTarget(kind="video_wall")
            self.active_drag_axis = None
            return
        self.selected_target = SelectionTarget(kind="fixture", fixture_id=key)
        self.active_drag_axis = None

    def get_floor_size_feet(self) -> float:
        return self.position_manager.get_floor_size_feet()

    def set_floor_size_feet(self, floor_size_feet: float) -> None:
        self.position_manager.venue_metadata["floor_size_feet"] = float(floor_size_feet)
        if self.room_renderer is not None:
            self.room_renderer.set_floor_size_feet(float(floor_size_feet))
        self.position_manager.save_current_venue_layout()

    def add_venue(self, display_name: str) -> None:
        venue = add_custom_venue(display_name)
        self.state.set_venue(venue)
        self.selected_target = None
        self.mode = "select"

    def add_light(self, fixture_type: str, address: int) -> None:
        fixture = add_fixture_to_venue(self.state.venue, fixture_type, address)
        self.position_manager.reload_current_venue_layout()

        occupied_positions = [
            renderer.position for renderer in self.renderers if renderer is not None
        ]
        new_x, new_y, new_z = self._next_default_fixture_position(occupied_positions)
        self.position_manager.set_fixture_position(fixture, new_x, new_y, new_z)
        self.position_manager.set_fixture_orientation(
            fixture, np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32)
        )
        self.position_manager.save_current_venue_layout()

        if self.patch_change_callback is not None:
            self.patch_change_callback()
        self.selected_target = SelectionTarget(kind="fixture", fixture_id=fixture.id)
        self.mode = "move"

    def render_gizmo(self) -> None:
        if (
            self.room_renderer is None
            or self.selected_target is None
            or self.mode not in ("move", "rotate")
        ):
            return

        origin = self._get_selected_origin()
        if origin is None:
            return

        active_axis = self.active_drag_axis if self.mode == "move" else None
        self.room_renderer.render_axis_gizmo(
            origin,
            active_axis=active_axis,
            axis_length=self.gizmo_axis_length,
        )

    def _on_mouse_press(self, x: float, y: float) -> bool:
        if not self._editor_enabled():
            return False

        if self.selected_target is not None and self.mode in ("move", "rotate"):
            handle = self._pick_axis_handle(x, y)
            if handle is not None:
                axis_name, direction = handle
                if self.mode == "move":
                    self.active_drag_axis = axis_name
                else:
                    self._rotate_selected(axis_name, direction)
                return True

        picked_target = self._pick_target(x, y)
        if picked_target is not None:
            self.selected_target = picked_target
            self.active_drag_axis = None
            return True

        return False

    def _on_mouse_drag(self, dx: float, dy: float) -> bool:
        if (
            not self._editor_enabled()
            or self.mode != "move"
            or self.active_drag_axis is None
        ):
            return False

        origin = self._get_selected_origin()
        if origin is None or self.room_renderer is None:
            return False

        axis_vector = self._axis_unit_vectors()[self.active_drag_axis]
        axis_end = (
            origin[0] + axis_vector[0],
            origin[1] + axis_vector[1],
            origin[2] + axis_vector[2],
        )
        screen_origin = self.room_renderer.project_world_to_screen(origin)
        screen_end = self.room_renderer.project_world_to_screen(axis_end)
        if screen_origin is None or screen_end is None:
            return True

        axis_screen = np.array(
            [screen_end[0] - screen_origin[0], screen_end[1] - screen_origin[1]],
            dtype=np.float32,
        )
        axis_length = float(np.linalg.norm(axis_screen))
        if axis_length < 1e-5:
            return True

        axis_unit = axis_screen / axis_length
        projected_pixels = float(dx * axis_unit[0] + dy * axis_unit[1])
        world_delta = projected_pixels / axis_length
        self._move_selected(self.active_drag_axis, world_delta)
        return True

    def _on_mouse_release(self, x: float, y: float) -> bool:
        if self.active_drag_axis is not None:
            self.active_drag_axis = None
            if self.layout_dirty:
                self.position_manager.save_current_venue_layout()
                self.layout_dirty = False
            return True
        if self.layout_dirty:
            self.position_manager.save_current_venue_layout()
            self.layout_dirty = False
        return False

    def _editor_enabled(self) -> bool:
        return self.state.show_fixture_mode and self.room_renderer is not None

    def _axis_unit_vectors(self) -> dict[str, tuple[float, float, float]]:
        return {
            "x": (1.0, 0.0, 0.0),
            "y": (0.0, 1.0, 0.0),
            "z": (0.0, 0.0, 1.0),
        }

    def _get_selected_renderer(self) -> Any | None:
        if self.selected_target is None or self.selected_target.kind != "fixture":
            return None
        for renderer in self.renderers:
            if renderer.fixture.id == self.selected_target.fixture_id:
                return renderer
        return None

    def _get_selected_origin(self) -> Optional[tuple[float, float, float]]:
        if self.selected_target is None:
            return None
        if self.selected_target.kind == "video_wall":
            return (
                float(self.video_wall_config["x"]),
                float(self.video_wall_config["y"]),
                float(self.video_wall_config["z"]),
            )

        renderer = self._get_selected_renderer()
        if renderer is None:
            return None
        return renderer.get_3d_position(self.canvas_size)

    def _pick_target(self, mouse_x: float, mouse_y: float) -> Optional[SelectionTarget]:
        if self.room_renderer is None:
            return None

        closest_target: Optional[SelectionTarget] = None
        closest_distance = self.selection_threshold_px

        for renderer in self.renderers:
            screen_pos = self.room_renderer.project_world_to_screen(
                renderer.get_3d_position(self.canvas_size)
            )
            if screen_pos is None:
                continue
            distance = self._screen_distance(screen_pos, (mouse_x, mouse_y))
            if distance < closest_distance:
                closest_distance = distance
                closest_target = SelectionTarget(
                    kind="fixture", fixture_id=renderer.fixture.id
                )

        video_wall_screen = self.room_renderer.project_world_to_screen(
            (
                float(self.video_wall_config["x"]),
                float(self.video_wall_config["y"]),
                float(self.video_wall_config["z"]),
            )
        )
        if video_wall_screen is not None:
            distance = self._screen_distance(video_wall_screen, (mouse_x, mouse_y))
            if distance < closest_distance + 18.0:
                closest_target = SelectionTarget(kind="video_wall")

        return closest_target

    def _pick_axis_handle(
        self, mouse_x: float, mouse_y: float
    ) -> Optional[tuple[str, int]]:
        origin = self._get_selected_origin()
        if origin is None or self.room_renderer is None:
            return None

        closest_handle: Optional[tuple[str, int]] = None
        closest_distance = self.selection_threshold_px

        for axis_name, axis_vector in self._axis_unit_vectors().items():
            for direction in (-1, 1):
                handle_world = (
                    origin[0] + axis_vector[0] * self.gizmo_axis_length * direction,
                    origin[1] + axis_vector[1] * self.gizmo_axis_length * direction,
                    origin[2] + axis_vector[2] * self.gizmo_axis_length * direction,
                )
                screen_pos = self.room_renderer.project_world_to_screen(handle_world)
                if screen_pos is None:
                    continue
                distance = self._screen_distance(screen_pos, (mouse_x, mouse_y))
                if distance < closest_distance:
                    closest_distance = distance
                    closest_handle = (axis_name, direction)

        return closest_handle

    def _move_selected(self, axis_name: str, world_delta: float) -> None:
        origin = self._get_selected_origin()
        if origin is None or self.room_renderer is None:
            return

        axis_index = {"x": 0, "y": 1, "z": 2}[axis_name]
        next_origin = [origin[0], origin[1], origin[2]]
        next_origin[axis_index] += world_delta

        if self.selected_target is None:
            return

        if self.selected_target.kind == "video_wall":
            self.position_manager.venue_metadata["video_wall"][axis_name] = float(
                next_origin[axis_index]
            )
            self.video_wall_config = self.position_manager.get_video_wall_config()
        else:
            renderer = self._get_selected_renderer()
            if renderer is None:
                return
            canvas_x, canvas_y, height = self.room_renderer.convert_3d_to_2d(
                float(next_origin[0]), float(next_origin[1]), float(next_origin[2])
            )
            self.position_manager.set_fixture_position(
                renderer.fixture, canvas_x, canvas_y, height
            )
            renderer.set_position(canvas_x, canvas_y, height)

        self.layout_dirty = True

    def _rotate_selected(self, axis_name: str, direction: int) -> None:
        if self.selected_target is None or self.selected_target.kind != "fixture":
            return

        renderer = self._get_selected_renderer()
        if renderer is None:
            return

        axis_vector = np.array(self._axis_unit_vectors()[axis_name], dtype=np.float32)
        delta_quaternion = quaternion_from_axis_angle(
            axis_vector, direction * (np.pi / 4.0)
        )
        updated_orientation = quaternion_multiply(
            delta_quaternion, renderer.orientation
        )
        renderer.orientation = updated_orientation
        self.position_manager.set_fixture_orientation(
            renderer.fixture, updated_orientation
        )
        self.position_manager.save_current_venue_layout()

    def _screen_distance(
        self, point_a: tuple[float, float], point_b: tuple[float, float]
    ) -> float:
        return float(
            np.linalg.norm(
                np.array([point_a[0] - point_b[0], point_a[1] - point_b[1]])
            )
        )

    def _next_default_fixture_position(
        self, occupied_positions: list[tuple[float, float, float]]
    ) -> tuple[float, float, float]:
        if not occupied_positions:
            return (250.0, 250.0, 3.0)

        max_x = max(position[0] for position in occupied_positions)
        max_y = max(position[1] for position in occupied_positions)
        next_x = max_x + 60.0
        next_y = max_y
        if next_x > 460.0:
            next_x = 40.0
            next_y = max_y + 60.0
        return (next_x, next_y, 3.0)

    def get_current_venue_label(self) -> str:
        return get_venue_display_name(self.state.venue)
