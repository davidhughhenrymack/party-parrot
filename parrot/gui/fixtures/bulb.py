from parrot.director.frame import Frame
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

    def setup(self, canvas: Canvas):
        self.oval = canvas.create_oval(
            self.x,
            self.y,
            self.x + self.width,
            self.y + self.height,
            fill="black",
            outline="black",
        )

    def set_position(self, canvas: Canvas, x: int, y: int):
        super().set_position(canvas, x, y)
        canvas.coords(
            self.oval, self.x, self.y, self.x + self.width, self.y + self.height
        )

    def render(self, canvas: Canvas, frame: Frame):
        color = self.fixture.get_color()
        dim = self.fixture.get_dimmer()

        canvas.itemconfig(self.oval, fill=dim_color(color, dim / 255))
