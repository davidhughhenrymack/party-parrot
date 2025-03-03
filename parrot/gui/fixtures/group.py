from typing import List
from tkinter import Canvas

from parrot.fixtures.base import FixtureGroup
from parrot.director.frame import Frame
from parrot.gui.fixtures.base import FixtureGuiRenderer


class FixtureGroupRenderer(FixtureGuiRenderer[FixtureGroup]):
    """Renderer for a group of fixtures."""

    def __init__(self, fixture_group: FixtureGroup):
        super().__init__(fixture_group)
        self.fixture_renderers = []  # Will be populated in setup_renderers
        self._width = 100  # Default width
        self._height = 50  # Default height

    def setup_renderers(self, renderer_factory):
        """Set up the renderers for each fixture in the group.

        This method must be called after initialization to avoid circular imports.
        """
        self.fixture_renderers = [
            renderer_factory(fixture) for fixture in self.fixture.fixtures
        ]

    @property
    def width(self) -> int:
        return self._width

    @property
    def height(self) -> int:
        return self._height

    def setup(self, canvas: Canvas):
        """Set up all fixture renderers in the group."""
        for renderer in self.fixture_renderers:
            renderer.setup(canvas)

        # Calculate the total width and height
        self._width = sum(
            renderer.width for renderer in self.fixture_renderers
        ) + 10 * (len(self.fixture_renderers) - 1)
        self._height = (
            max(renderer.height for renderer in self.fixture_renderers)
            if self.fixture_renderers
            else 0
        )

    def set_position(self, canvas: Canvas, x: int, y: int):
        """Set the position of the group and arrange all fixtures horizontally."""
        super().set_position(canvas, x, y)

        # Arrange fixtures horizontally
        current_x = x
        for renderer in self.fixture_renderers:
            renderer.set_position(canvas, current_x, y)
            current_x += renderer.width + 10  # 10px spacing between fixtures

    def render(self, canvas: Canvas, frame: Frame):
        """Render all fixtures in the group."""
        for renderer in self.fixture_renderers:
            renderer.render(canvas, frame)

        # Group labels are now disabled
        # canvas.create_text(
        #     self.x,
        #     self.y - 15,  # Position above the fixtures
        #     text=self.fixture.name,
        #     fill="white",
        #     anchor="w"
        # )

    def to_json(self):
        """Convert the renderer state to JSON."""
        data = super().to_json()
        data["renderers"] = [renderer.to_json() for renderer in self.fixture_renderers]
        return data

    def from_json(self, canvas, data):
        """Restore the renderer state from JSON."""
        super().from_json(canvas, data)
        if "renderers" in data and len(data["renderers"]) == len(
            self.fixture_renderers
        ):
            for i, renderer_data in enumerate(data["renderers"]):
                self.fixture_renderers[i].from_json(canvas, renderer_data)

    def contains_point(self, x, y):
        """Check if the given point is inside the group's area."""
        # No longer including the label area since we're not displaying labels
        return (
            self.x <= x <= self.x + self.width and self.y <= y <= self.y + self.height
        )
