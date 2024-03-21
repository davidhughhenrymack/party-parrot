from typing import Generic, List, TypeVar
from parrot.fixtures.base import FixtureBase
from tkinter import Canvas
from parrot.director.frame import Frame

T = TypeVar("T", bound=FixtureBase)


class FixtureGuiRenderer(Generic[T]):
    def __init__(self, fixture: T):
        self.fixture = fixture

    @property
    def width(self) -> int:
        raise NotImplementedError

    @property
    def height(self) -> int:
        raise NotImplementedError

    def setup(self, canvas: Canvas, x: int, y: int):
        pass

    def render(self, canvas: Canvas, frame: Frame):
        pass
