from .base import FixtureGuiRenderer
from parrot.fixtures import FixtureBase
from tkinter import Canvas
from parrot.utils.color_extra import dim_color

CIRCLE_SIZE = 30


class BulbRenderer(FixtureGuiRenderer[FixtureBase]):
    def __init__(self, fixture: FixtureBase):
        super().__init__(fixture)

    @property
    def width(self) -> int:
        return 30

    @property
    def height(self) -> int:
        return 30

    def setup(self, canvas: Canvas, x: int, y: int):
        self.oval = canvas.create_oval(
            x, y, x + self.width, y + self.height, fill="black"
        )

    def render(self, canvas: Canvas):
        color = self.fixture.get_color()
        dim = self.fixture.get_dimmer()

        canvas.itemconfig(self.oval, fill=dim_color(color, dim / 255))
