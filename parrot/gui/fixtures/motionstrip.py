from .base import FixtureGuiRenderer
from parrot.fixtures import FixtureBase
from tkinter import Canvas
from parrot.utils.color_extra import dim_color


class MotionstripRenderer(FixtureGuiRenderer[FixtureBase]):
    def __init__(self, fixture: FixtureBase):
        super().__init__(fixture)

    @property
    def width(self) -> int:
        return 50

    @property
    def height(self) -> int:
        return 20

    def setup(self, canvas: Canvas, x: int, y: int):
        self.shape = canvas.create_rectangle(
            x,
            y,
            x + self.width,
            y + self.height,
            fill="black",
        )

    def render(self, canvas: Canvas):
        color = self.fixture.get_color()
        dim = self.fixture.get_dimmer()

        canvas.itemconfig(self.shape, fill=dim_color(color, dim))
