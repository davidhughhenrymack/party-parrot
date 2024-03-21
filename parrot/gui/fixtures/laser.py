import random

from parrot.utils.colour import Color
from parrot.director.frame import Frame
from .base import FixtureGuiRenderer
from parrot.fixtures import FixtureBase
from tkinter import Canvas
from parrot.utils.color_extra import dim_color
import math

LINES = 8
LINE_R = 30

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
            outline="black",
        )

        self.lines = []
        for i in range(LINES):
            size = LINE_R * random.random()
            angle = random.random() * 2 * math.pi
            self.lines.append(
                canvas.create_line(
                    cx,
                    cy,
                    cx + size * math.cos(angle),
                    cy + size * math.sin(angle),
                    fill="",
                    width=1,
                )
            )

    def render(self, canvas: Canvas, frame: Frame):
        dim = self.fixture.get_dimmer()

        if dim < 10:
            for i in self.lines:
                canvas.itemconfig(i, fill="")

        else:
            for i in self.lines:
                canvas.itemconfig(
                    i,
                    fill=dim_color(
                        Color("white"),
                        dim * (0.5 + math.cos(i + 4 * frame.time / 2) / 2),
                    ),
                )
