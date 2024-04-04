from typing import Generic, List, TypeVar
from parrot.fixtures.base import FixtureBase
from tkinter import Canvas
from parrot.director.frame import Frame

T = TypeVar("T", bound=FixtureBase)


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
