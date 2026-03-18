#!/usr/bin/env python3

import json
import os
import numpy as np
from beartype import beartype
from typing import Any, Optional
from parrot.state import State
from parrot.patch_bay import get_default_venue_metadata, venue_patches
from parrot.fixtures.base import FixtureBase, FixtureGroup


@beartype
class FixturePositionManager:
    """
    Manages fixture positions loaded from JSON files.
    Applies positions to fixture objects so they can be used by spatial interpreters
    and renderers. Uses patch_bay as the golden source of fixtures.
    """

    def __init__(self, state: State):
        """
        Args:
            state: Global state object (provides current venue)
        """
        self.state = state
        self.venue_metadata: dict[str, Any] = {}
        self._loaded_layout_data: dict[str, Any] = {}

        # Subscribe to venue changes to reload positions
        self.state.events.on_venue_change += self._on_venue_change

        # Load positions for the current venue
        self._load_and_apply_positions()

    def _on_venue_change(self, venue):
        """Reload positions when venue changes"""
        self._load_and_apply_positions()

    def reload_current_venue_layout(self) -> None:
        self._load_and_apply_positions()

    def _get_all_fixtures(self) -> list[FixtureBase]:
        """Get all fixtures from the current venue's patch bay, flattening groups"""
        from parrot.patch_bay import get_manual_group

        fixtures = []
        for item in venue_patches[self.state.venue]:
            if isinstance(item, FixtureGroup):
                # Add all fixtures from the group
                for fixture in item.fixtures:
                    fixtures.append(fixture)
            else:
                # Individual fixture
                fixtures.append(item)

        # Also include manual fixtures (actor/performance lights)
        manual_group = get_manual_group(self.state.venue)
        if manual_group is not None:
            for fixture in manual_group.fixtures:
                fixtures.append(fixture)

        return fixtures

    def _load_and_apply_positions(self):
        """Load fixture positions from JSON file and apply them to fixture objects"""
        filename = self.get_layout_filename()

        # Get all fixtures from patch bay (golden source)
        fixtures = self._get_all_fixtures()
        self.venue_metadata = get_default_venue_metadata(self.state.venue)
        self._loaded_layout_data = {}

        if not os.path.exists(filename):
            # Use default positions if no saved file
            self._apply_default_positions(fixtures)
            return

        try:
            with open(filename, "r") as f:
                data = json.load(f)
            self._loaded_layout_data = data

            venue_metadata = data.get("__venue__")
            if isinstance(venue_metadata, dict):
                self.venue_metadata["floor_size_feet"] = float(
                    venue_metadata.get(
                        "floor_size_feet", self.venue_metadata["floor_size_feet"]
                    )
                )
                video_wall = venue_metadata.get("video_wall")
                if isinstance(video_wall, dict):
                    merged_video_wall = dict(self.venue_metadata["video_wall"])
                    for key in ("x", "y", "z", "width", "height"):
                        if key in video_wall:
                            merged_video_wall[key] = float(video_wall[key])
                    self.venue_metadata["video_wall"] = merged_video_wall

            # Apply positions to fixtures
            for fixture in fixtures:
                if fixture.id in data:
                    pos_data = data[fixture.id]
                    x = float(pos_data.get("x", 0))
                    y = float(pos_data.get("y", 0))
                    z = float(pos_data.get("z", 3.0))  # Default height of 3

                    # Set position attributes on the fixture object
                    fixture.x = x
                    fixture.y = y
                    fixture.z = z

                    # Load orientation if present (as numpy array)
                    if "orientation" in pos_data:
                        orientation = pos_data["orientation"]
                        fixture.orientation = np.array(orientation, dtype=np.float32)
                    else:
                        # Default orientation (identity quaternion)
                        fixture.orientation = np.array(
                            [0.0, 0.0, 0.0, 1.0], dtype=np.float32
                        )
                else:
                    # Fixture not in saved data, use default
                    self._apply_default_position(fixture)

            print(f"Loaded positions for {len(fixtures)} fixtures from {filename}")

        except Exception as e:
            print(f"Error loading fixture positions from {filename}: {e}")
            self._apply_default_positions(fixtures)

    def _apply_default_positions(self, fixtures: list[FixtureBase]):
        """Apply default positions to all fixtures (grid layout)"""
        fixture_margin = 10.0
        x = fixture_margin
        y = fixture_margin
        max_row_height = 50.0  # Default fixture height
        canvas_width = 1200.0

        for fixture in fixtures:
            # Assume default size for layout
            width = 50.0
            height = 50.0

            # Check if we need to wrap to next row
            if x + width > canvas_width - fixture_margin:
                x = fixture_margin
                y += max_row_height + fixture_margin
                max_row_height = 50.0

            fixture.x = x
            fixture.y = y
            fixture.z = 3.0
            fixture.orientation = np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32)

            x += width + fixture_margin

        print(f"Applied default positions to {len(fixtures)} fixtures")

    def _apply_default_position(self, fixture: FixtureBase):
        """Apply default position to a single fixture"""
        fixture.x = 10.0
        fixture.y = 10.0
        fixture.z = 3.0
        fixture.orientation = np.array([0.0, 0.0, 0.0, 1.0], dtype=np.float32)

    def get_layout_filename(self) -> str:
        return f"{self.state.venue.name}_gui.json"

    def get_fixture_position(
        self, fixture: FixtureBase
    ) -> Optional[tuple[float, float, float]]:
        """
        Get the position of a fixture as a tuple (x, y, z).
        Returns None if position is not set.
        """
        x = getattr(fixture, "x", None)
        y = getattr(fixture, "y", None)
        z = getattr(fixture, "z", None)
        if x is not None and y is not None and z is not None:
            return (float(x), float(y), float(z))
        return None

    def get_fixture_orientation(self, fixture: FixtureBase) -> Optional[np.ndarray]:
        """
        Get the orientation of a fixture as a quaternion (numpy array).
        Returns None if orientation is not set.
        """
        orientation = getattr(fixture, "orientation", None)
        if orientation is not None:
            return orientation
        return None

    def set_fixture_position(
        self, fixture: FixtureBase, x: float, y: float, z: float
    ) -> None:
        fixture.x = float(x)
        fixture.y = float(y)
        fixture.z = float(z)

    def set_fixture_orientation(
        self, fixture: FixtureBase, orientation: np.ndarray
    ) -> None:
        fixture.orientation = np.array(orientation, dtype=np.float32)

    def save_current_venue_layout(self) -> None:
        fixtures = self._get_all_fixtures()
        data: dict[str, Any] = {
            "__venue__": {
                "floor_size_feet": float(self.venue_metadata["floor_size_feet"]),
                "video_wall": dict(self.venue_metadata["video_wall"]),
            }
        }
        for fixture in fixtures:
            position = self.get_fixture_position(fixture)
            orientation = self.get_fixture_orientation(fixture)
            if position is None or orientation is None:
                continue
            data[fixture.id] = {
                "x": float(position[0]),
                "y": float(position[1]),
                "z": float(position[2]),
                "orientation": [float(value) for value in orientation.tolist()],
            }

        with open(self.get_layout_filename(), "w") as handle:
            json.dump(data, handle, indent=2)

    def get_floor_size_feet(self) -> float:
        return float(self.venue_metadata["floor_size_feet"])

    def set_floor_size_feet(self, floor_size_feet: float) -> None:
        self.venue_metadata["floor_size_feet"] = float(floor_size_feet)
        self.save_current_venue_layout()

    def get_video_wall_config(self) -> dict[str, float]:
        return dict(self.venue_metadata["video_wall"])

    def set_video_wall_config(self, video_wall: dict[str, float]) -> None:
        merged_video_wall = dict(self.venue_metadata["video_wall"])
        for key in ("x", "y", "z", "width", "height"):
            if key in video_wall:
                merged_video_wall[key] = float(video_wall[key])
        self.venue_metadata["video_wall"] = merged_video_wall
        self.save_current_venue_layout()
