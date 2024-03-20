from .base import FixtureGuiRenderer
from parrot.fixtures import FixtureBase
from tkinter import Canvas
from parrot.utils.color_extra import dim_color
import math

LINES = 5
LINE_R = 20

BOX_W = 30
BOX_H = 15


class LaserRenderer(FixtureGuiRenderer[FixtureBase]):
    def __init__(self, fixture: FixtureBase):
        super().__init__(fixture)

    @property
    def width(self) -> int:
        return 50

    @property
    def height(self) -> int:
        return 50

    def setup(self, canvas: Canvas, x: int, y: int):

        cx = x + self.width / 2
        cy = y + self.height / 2

        self.shape = canvas.create_rectangle(
            cx - BOX_W / 2,
            cy - BOX_H / 2,
            cx + BOX_W / 2,
            cy + BOX_H / 2,
            fill="black",
        )

        self.lines = [
            canvas.create_line(
                cx,
                cy,
                cx + LINE_R * math.cos(i / math.pi),
                cy + LINE_R * math.sin(i / math.pi),
                fill="",
            )
            for i in range(LINES)
        ]

    def render(self, canvas: Canvas):
        dim = self.fixture.get_dimmer()

        for i in self.lines:
            canvas.itemconfig(i, fill="white" if dim > 128 else "")
