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
        dim *= math.sin(frame.time * 30 * strobe / 255 * 4)

    return dim_color(color, dim / 255)


class FixtureGuiRenderer(Generic[T]):
    def __init__(self, fixture: T):
        self.fixture = fixture
        self._x = 0
        self._y = 0

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

    def setup(self, canvas: Canvas):
        pass

    def render(self, canvas: Canvas, frame: Frame):
        pass

    def to_json(self):
        return {
            "x": self.x,
            "y": self.y,
        }

    def from_json(self, canvas, data):
        self.set_position(canvas, data["x"], data["y"])
