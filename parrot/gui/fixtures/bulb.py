from parrot.director.frame import Frame
from .base import FixtureGuiRenderer, render_strobe_dim_color
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
        fill = render_strobe_dim_color(self.fixture, frame)
        canvas.itemconfig(self.oval, fill=fill)
