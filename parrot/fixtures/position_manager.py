#!/usr/bin/env python3

import json
import os
import numpy as np
from beartype import beartype
from typing import Optional
from parrot.state import State
from parrot.patch_bay import venue_patches
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

        # Subscribe to venue changes to reload positions
        self.state.events.on_venue_change += self._on_venue_change

        # Load positions for the current venue
        self._load_and_apply_positions()

    def _on_venue_change(self, venue):
        """Reload positions when venue changes"""
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
        filename = f"{self.state.venue.name}_gui.json"

        # Get all fixtures from patch bay (golden source)
        fixtures = self._get_all_fixtures()

        if not os.path.exists(filename):
            # Use default positions if no saved file
            self._apply_default_positions(fixtures)
            return

        try:
            with open(filename, "r") as f:
                data = json.load(f)

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

    def get_fixture_position(
        self, fixture: FixtureBase
    ) -> Optional[tuple[float, float, float]]:
        """
        Get the position of a fixture as a tuple (x, y, z).
        Returns None if position is not set.
        """
        if hasattr(fixture, "x") and hasattr(fixture, "y") and hasattr(fixture, "z"):
            return (fixture.x, fixture.y, fixture.z)
        return None

    def get_fixture_orientation(self, fixture: FixtureBase) -> Optional[np.ndarray]:
        """
        Get the orientation of a fixture as a quaternion (numpy array).
        Returns None if orientation is not set.
        """
        if hasattr(fixture, "orientation"):
            return fixture.orientation
        return None
