#!/usr/bin/env python3
"""
Fixture selection and manipulation system.
Handles mouse picking, 3D axes rendering, and dragging along axes.
"""

from beartype import beartype
from beartype.typing import Optional
import numpy as np
import math

from parrot.vj.renderers.base import FixtureRenderer
from parrot.fixtures.position_manager import FixturePositionManager
from parrot.state import State


@beartype
class FixtureSelection:
    """Manages fixture selection and 3D manipulation with axes"""

    def __init__(
        self,
        position_manager: FixturePositionManager,
        state: State,
    ):
        self.position_manager = position_manager
        self.state = state

        # Selection state
        self.selected_renderer: Optional[FixtureRenderer] = None
        self.selected_axis: Optional[str] = None  # 'x', 'y', 'z', or None

        # Drag state
        self.drag_start_position: Optional[tuple[float, float, float]] = None
        self.drag_start_mouse: Optional[tuple[float, float]] = None
        self.is_dragging = False

        # Axis visual parameters
        self.axis_length = 1.5
        self.axis_thickness = 0.05
        self.axis_hover_distance = 0.3  # Distance within which axis is hoverable

    def handle_mouse_press(
        self,
        mouse_x: float,
        mouse_y: float,
        window_width: int,
        window_height: int,
        renderers: list[FixtureRenderer],
        room_renderer,
        canvas_size: tuple[float, float],
    ):
        """Handle mouse press for selection or axis dragging

        Args:
            mouse_x: Mouse x coordinate (window space)
            mouse_y: Mouse y coordinate (window space)
            window_width: Window width in pixels
            window_height: Window height in pixels
            renderers: List of all fixture renderers
            room_renderer: Room3DRenderer instance for raycasting
            canvas_size: (width, height) of the fixture canvas coordinate system
        """
        # Check if we're clicking on an axis of the selected fixture
        if self.selected_renderer is not None:
            axis = self._ray_intersect_axes(
                mouse_x,
                mouse_y,
                window_width,
                window_height,
                room_renderer,
                canvas_size,
            )
            if axis is not None:
                # Start dragging the axis
                print(f"🎯 Starting drag on {axis} axis")
                self.selected_axis = axis
                self.is_dragging = True
                self.drag_start_mouse = (mouse_x, mouse_y)
                self.drag_start_position = self.selected_renderer.position
                return

        # Otherwise, check if we're clicking on a fixture
        clicked_renderer = self._ray_intersect_fixtures(
            mouse_x,
            mouse_y,
            window_width,
            window_height,
            renderers,
            room_renderer,
            canvas_size,
        )

        if clicked_renderer is not None:
            # Select the clicked fixture
            self.selected_renderer = clicked_renderer
            self.selected_axis = None
        else:
            # Click on empty space - deselect
            self.selected_renderer = None
            self.selected_axis = None

    def handle_mouse_drag(
        self,
        mouse_x: float,
        mouse_y: float,
        window_width: int,
        window_height: int,
        room_renderer,
        canvas_size: tuple[float, float],
    ):
        """Handle mouse drag for axis manipulation

        Args:
            mouse_x: Current mouse x coordinate
            mouse_y: Current mouse y coordinate
            window_width: Window width in pixels
            window_height: Window height in pixels
            room_renderer: Room3DRenderer instance
            canvas_size: (width, height) of the fixture canvas coordinate system
        """
        print(
            f"🖱️  handle_mouse_drag: is_dragging={self.is_dragging}, axis={self.selected_axis}"
        )

        if (
            not self.is_dragging
            or self.selected_axis is None
            or self.selected_renderer is None
        ):
            return

        if self.drag_start_mouse is None or self.drag_start_position is None:
            return

        # Calculate movement along the selected axis
        dx = mouse_x - self.drag_start_mouse[0]
        dy = mouse_y - self.drag_start_mouse[1]

        # Convert screen-space delta to world-space delta along the axis
        # Use simple heuristic: horizontal drag affects X/Z, vertical drag affects Y
        movement_scale = 0.02  # Scale factor for mouse-to-world movement

        old_x, old_y, old_z = self.drag_start_position
        new_x, new_y, new_z = old_x, old_y, old_z

        if self.selected_axis == "x":
            # X axis: move left/right based on horizontal mouse movement
            new_x = old_x + dx * movement_scale * canvas_size[0]
        elif self.selected_axis == "y":
            # Y axis: move up/down based on vertical mouse movement (inverted)
            new_y = old_y - dy * movement_scale * 10.0  # Z is height, scale differently
        elif self.selected_axis == "z":
            # Z axis: move forward/back based on vertical mouse movement
            new_z = old_z + dy * movement_scale * canvas_size[1]

        # Update renderer position
        print(f"  📍 Moving fixture to ({new_x:.1f}, {new_y:.1f}, {new_z:.1f})")
        self.selected_renderer.set_position(new_x, new_y, new_z)

        # Update fixture object position
        fixture = self.selected_renderer.fixture
        fixture.x = new_x
        fixture.y = new_y
        fixture.z = new_z

    def handle_mouse_release(self):
        """Handle mouse release - end dragging and save position"""
        if self.is_dragging and self.selected_renderer is not None:
            # Save the new position to JSON
            self._save_positions()

        self.is_dragging = False
        self.selected_axis = None
        self.drag_start_mouse = None
        self.drag_start_position = None

    def _save_positions(self):
        """Save all fixture positions to JSON file"""
        import json
        import os

        filename = f"{self.state.venue.name}_gui.json"

        # Get all fixtures from patch bay
        fixtures = self.position_manager._get_all_fixtures()

        # Build position data
        data = {}
        for fixture in fixtures:
            if (
                hasattr(fixture, "x")
                and hasattr(fixture, "y")
                and hasattr(fixture, "z")
            ):
                pos_data = {
                    "x": float(fixture.x),
                    "y": float(fixture.y),
                    "z": float(fixture.z),
                }
                # Save orientation if present
                if hasattr(fixture, "orientation"):
                    pos_data["orientation"] = fixture.orientation.tolist()

                data[fixture.id] = pos_data

        # Write to file
        try:
            with open(filename, "w") as f:
                json.dump(data, f, indent=2)
            print(f"💾 Saved fixture positions to {filename}")
        except Exception as e:
            print(f"❌ Error saving positions: {e}")

    def _ray_intersect_fixtures(
        self,
        mouse_x: float,
        mouse_y: float,
        window_width: int,
        window_height: int,
        renderers: list[FixtureRenderer],
        room_renderer,
        canvas_size: tuple[float, float],
    ) -> Optional[FixtureRenderer]:
        """Cast ray from mouse position and find intersected fixture

        Returns:
            The clicked fixture renderer, or None if no fixture was clicked
        """
        # Generate ray from camera through mouse position
        ray_origin, ray_direction = self._get_mouse_ray(
            mouse_x, mouse_y, window_width, window_height, room_renderer
        )

        # Check intersection with each fixture (test against their bounding boxes)
        closest_renderer = None
        closest_distance = float("inf")

        for renderer in renderers:
            # Get 3D position of fixture
            position_3d = renderer.get_3d_position(canvas_size)

            # Use simple sphere intersection for fixture body
            # Make radius larger for easier clicking (5x the cube size)
            fixture_radius = renderer.cube_size * 5.0

            distance = self._ray_sphere_intersection(
                ray_origin, ray_direction, position_3d, fixture_radius
            )

            if distance is not None and distance < closest_distance:
                closest_distance = distance
                closest_renderer = renderer

        return closest_renderer

    def _ray_intersect_axes(
        self,
        mouse_x: float,
        mouse_y: float,
        window_width: int,
        window_height: int,
        room_renderer,
        canvas_size: tuple[float, float],
    ) -> Optional[str]:
        """Check if mouse ray intersects any manipulation axis

        Returns:
            'x', 'y', 'z', or None if no axis is hit
        """
        if self.selected_renderer is None:
            return None

        # Generate ray from camera
        ray_origin, ray_direction = self._get_mouse_ray(
            mouse_x, mouse_y, window_width, window_height, room_renderer
        )

        # Get fixture position
        position_3d = self.selected_renderer.get_3d_position(canvas_size)

        # Check each axis (model as cylinders for easier clicking)
        axes = [
            ("x", np.array([1.0, 0.0, 0.0], dtype=np.float32)),
            ("y", np.array([0.0, 1.0, 0.0], dtype=np.float32)),
            ("z", np.array([0.0, 0.0, 1.0], dtype=np.float32)),
        ]

        closest_axis = None
        closest_distance = float("inf")

        for axis_name, axis_direction in axes:
            # Check intersection with axis line (as a cylinder)
            distance = self._ray_cylinder_intersection(
                ray_origin,
                ray_direction,
                np.array(position_3d, dtype=np.float32),
                axis_direction,
                self.axis_length,
                self.axis_thickness * 2,  # Make it easier to click
            )

            if distance is not None and distance < closest_distance:
                closest_distance = distance
                closest_axis = axis_name

        return closest_axis

    def _get_mouse_ray(
        self,
        mouse_x: float,
        mouse_y: float,
        window_width: int,
        window_height: int,
        room_renderer,
    ) -> tuple[np.ndarray, np.ndarray]:
        """Convert mouse position to 3D ray in world space

        Returns:
            (ray_origin, ray_direction) in world coordinates
        """
        # Normalize mouse coordinates to [-1, 1]
        ndc_x = (2.0 * mouse_x) / window_width - 1.0
        ndc_y = 1.0 - (2.0 * mouse_y) / window_height  # Flip Y

        # Get camera parameters from room renderer
        fov = 60.0  # Degrees (matches room_renderer)
        aspect = window_width / window_height

        # Calculate camera position (same as in room_renderer._get_mvp_matrix)
        horizontal_distance = room_renderer.camera_distance * math.cos(
            room_renderer.camera_tilt
        )
        cam_x = horizontal_distance * math.sin(room_renderer.camera_angle)
        cam_z = horizontal_distance * math.cos(room_renderer.camera_angle)
        cam_y = room_renderer.camera_height + room_renderer.camera_distance * math.sin(
            room_renderer.camera_tilt
        )

        ray_origin = np.array([cam_x, cam_y, cam_z], dtype=np.float32)

        # Calculate ray direction in camera space
        fov_rad = math.radians(fov)
        tan_half_fov = math.tan(fov_rad / 2.0)

        # Ray direction in camera space
        ray_dir_x = ndc_x * aspect * tan_half_fov
        ray_dir_y = ndc_y * tan_half_fov
        ray_dir_z = -1.0  # Looking down -Z in camera space

        # Camera looks at center of room
        center = np.array(
            [0.0, room_renderer.camera_height * 0.5, 0.0], dtype=np.float32
        )
        up = np.array([0.0, 1.0, 0.0], dtype=np.float32)

        # Calculate camera basis vectors
        forward = center - ray_origin
        forward = forward / np.linalg.norm(forward)

        right = np.cross(forward, up)
        right = right / np.linalg.norm(right)

        camera_up = np.cross(right, forward)

        # Transform ray direction to world space
        ray_direction = (
            right * ray_dir_x
            + camera_up * ray_dir_y
            + forward * (-ray_dir_z)  # Negate because camera looks down -Z
        )
        ray_direction = ray_direction / np.linalg.norm(ray_direction)

        return ray_origin, ray_direction

    def _ray_sphere_intersection(
        self,
        ray_origin: np.ndarray,
        ray_direction: np.ndarray,
        sphere_center: tuple[float, float, float],
        sphere_radius: float,
    ) -> Optional[float]:
        """Test ray-sphere intersection

        Returns:
            Distance along ray to intersection, or None if no intersection
        """
        center = np.array(sphere_center, dtype=np.float32)
        oc = ray_origin - center

        a = np.dot(ray_direction, ray_direction)
        b = 2.0 * np.dot(oc, ray_direction)
        c = np.dot(oc, oc) - sphere_radius * sphere_radius

        discriminant = b * b - 4 * a * c

        if discriminant < 0:
            return None

        # Return nearest intersection
        t = (-b - math.sqrt(discriminant)) / (2.0 * a)
        if t > 0:
            return t

        return None

    def _ray_cylinder_intersection(
        self,
        ray_origin: np.ndarray,
        ray_direction: np.ndarray,
        cylinder_start: np.ndarray,
        cylinder_direction: np.ndarray,
        cylinder_length: float,
        cylinder_radius: float,
    ) -> Optional[float]:
        """Test ray-cylinder intersection (finite cylinder)

        Returns:
            Distance along ray to intersection, or None if no intersection
        """
        # Simplified: check distance from ray to line segment
        # Calculate closest point on axis to the ray

        # Cylinder end point
        cylinder_end = cylinder_start + cylinder_direction * cylinder_length

        # Check distance from ray to the axis line segment
        # Use point-to-line-segment distance
        for t in np.linspace(0, 1, 20):  # Sample along the cylinder
            point = cylinder_start + cylinder_direction * cylinder_length * t

            # Find closest point on ray to this point
            to_point = point - ray_origin
            projection = np.dot(to_point, ray_direction)

            if projection < 0:
                continue

            closest_on_ray = ray_origin + ray_direction * projection
            distance_to_axis = np.linalg.norm(closest_on_ray - point)

            if distance_to_axis < cylinder_radius:
                return float(projection)

        return None

    def render_selection_highlight(
        self, room_renderer, canvas_size: tuple[float, float]
    ):
        """Render bright blue highlight on selected fixture body

        Args:
            room_renderer: Room3DRenderer instance
            canvas_size: (width, height) of the fixture canvas
        """
        if self.selected_renderer is None:
            return

        # Get 3D position
        position_3d = self.selected_renderer.get_3d_position(canvas_size)

        # Render bright blue cube overlay (slightly larger than fixture body)
        highlight_size = self.selected_renderer.cube_size * 1.1
        highlight_color = (0.0, 0.5, 1.0)  # Bright blue

        with room_renderer.local_position(position_3d):
            with room_renderer.local_rotation(self.selected_renderer.orientation):
                # Render slightly larger cube as highlight
                room_renderer.render_cube(
                    (0.0, 0.0, 0.0),
                    highlight_color,
                    highlight_size,
                )

    def render_manipulation_axes(self, room_renderer, canvas_size: tuple[float, float]):
        """Render 3D manipulation axes (X, Y, Z) on selected fixture

        Args:
            room_renderer: Room3DRenderer instance
            canvas_size: (width, height) of the fixture canvas
        """
        if self.selected_renderer is None:
            return

        # Get 3D position (center of fixture)
        position_3d = self.selected_renderer.get_3d_position(canvas_size)

        # Axis colors: X=red, Y=green, Z=blue
        axes = [
            ("x", (1.0, 0.0, 0.0), (1.0, 0.0, 0.0)),  # X: Red
            ("y", (0.0, 1.0, 0.0), (0.0, 1.0, 0.0)),  # Y: Green
            ("z", (0.0, 0.0, 1.0), (0.0, 0.0, 1.0)),  # Z: Blue
        ]

        with room_renderer.local_position(position_3d):
            for axis_name, color, direction in axes:
                # Brighten axis if it's selected
                if self.selected_axis == axis_name:
                    axis_color = (1.0, 1.0, 0.0)  # Yellow when selected
                    thickness = self.axis_thickness * 2.0
                else:
                    axis_color = color
                    thickness = self.axis_thickness

                # Render axis as a cone (arrow)
                if axis_name == "x":
                    direction_vec = (1.0, 0.0, 0.0)
                elif axis_name == "y":
                    direction_vec = (0.0, 1.0, 0.0)
                else:  # 'z'
                    direction_vec = (0.0, 0.0, 1.0)

                # Render axis line
                room_renderer.render_cone_beam(
                    0.0,
                    0.0,
                    0.0,  # Start at fixture center
                    direction_vec,
                    axis_color,
                    length=self.axis_length,
                    start_radius=thickness,
                    end_radius=thickness * 0.5,  # Taper slightly
                    segments=8,
                    alpha=0.8,
                )

                # Render arrow head at the end
                end_pos = np.array(direction_vec, dtype=np.float32) * self.axis_length
                room_renderer.render_emission_circle(
                    (float(end_pos[0]), float(end_pos[1]), float(end_pos[2])),
                    axis_color,
                    radius=thickness * 3.0,
                    normal=direction_vec,
                    alpha=0.9,
                )
