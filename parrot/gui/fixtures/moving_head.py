from .base import FixtureGuiRenderer
from parrot.fixtures import FixtureBase
from tkinter import Canvas
from parrot.utils.color_extra import dim_color


HEAD_WIDTH = 20
HEAD_HEIGHT = 25

BASE_WIDTH = 40
BASE_HEIGHT = 10

LIGHT_RADIUS = 7


class MovingHeadRenderer(FixtureGuiRenderer[FixtureBase]):
    def __init__(self, fixture: FixtureBase):
        super().__init__(fixture)

    @property
    def width(self) -> int:
        return 40

    @property
    def height(self) -> int:
        return 40

    def setup(self, canvas: Canvas, x: int, y: int):
        self.base = canvas.create_rectangle(
            x,
            y + self.height - BASE_HEIGHT,
            x + self.width,
            y + self.height,
            fill="black",
        )
        self.head = canvas.create_rectangle(
            x + self.height / 2 - HEAD_WIDTH / 2,
            y,
            x + self.height / 2 + HEAD_WIDTH / 2,
            y + HEAD_HEIGHT,
            fill="black",
        )

        self.light = canvas.create_oval(
            x + self.width / 2 - LIGHT_RADIUS,
            y + 5,
            x + self.width / 2 + LIGHT_RADIUS,
            y + 5 + 2 * LIGHT_RADIUS,
            fill="black",
        )

    def render(self, canvas: Canvas):
        color = self.fixture.get_color()
        dim = self.fixture.get_dimmer()

        canvas.itemconfig(self.light, fill=dim_color(color, dim / 255))
