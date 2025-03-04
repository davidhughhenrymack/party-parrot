import math
from typing import Generic, List, TypeVar
from parrot.fixtures.base import FixtureBase
from tkinter import Canvas
from parrot.director.frame import Frame
from parrot.utils.color_extra import dim_color

T = TypeVar("T", bound=FixtureBase)


def render_strobe_dim_color(fixture, frame):
    color = fixture.get_color()
    dim = fixture.get_dimmer()
    strobe = fixture.get_strobe()

    if strobe > 10:
        dim = 255 * (1 + math.sin(frame.time * 30 * strobe / 255 * 4) / 2)

    return dim_color(color, dim / 255)


class FixtureGuiRenderer(Generic[T]):
    def __init__(self, fixture: T):
        self.fixture = fixture
        self._x = 0
        self._y = 0
        self.patch_label = None

    @property
    def width(self) -> int:
        raise NotImplementedError

    @property
    def height(self) -> int:
        raise NotImplementedError

    @property
    def x(self) -> int:
        return self._x

    @property
    def y(self) -> int:
        return self._y

    def set_position(self, canvas: Canvas, x: int, y: int):
        self._x = x
        self._y = y
        # Update patch label position if it exists
        if self.patch_label:
            # Position the label above the fixture
            canvas.coords(self.patch_label, self._x + 2, self._y - 10)

    def setup(self, canvas: Canvas):
        # Create patch address label
        patch_text = ""
        if hasattr(self.fixture, "patch"):
            patch_text = str(self.fixture.patch)
        elif hasattr(self.fixture, "id") and "@" in self.fixture.id:
            # Try to extract patch from ID (format: "name@patch")
            try:
                patch_text = self.fixture.id.split("@")[1]
            except (IndexError, AttributeError):
                pass

        self.patch_label = canvas.create_text(
            self._x + 2,
            self._y - 10,  # Position the label above the fixture
            text=patch_text,
            fill="gray",
            anchor="nw",
            font=("Arial", 8),
        )

    def render(self, canvas: Canvas, frame: Frame):
        pass

    def to_json(self):
        return {
            "x": self.x,
            "y": self.y,
        }

    def from_json(self, canvas, data):
        self.set_position(canvas, data["x"], data["y"])

    def contains_point(self, x, y):
        """Check if the given point is inside the renderer's area.

        Args:
            x: X coordinate of the point
            y: Y coordinate of the point

        Returns:
            True if the point is inside the renderer's area, False otherwise
        """
        return (
            self.x <= x <= self.x + self.width and self.y <= y <= self.y + self.height
        )
