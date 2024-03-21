import math
from parrot.director.frame import Frame
from .base import FixtureGuiRenderer
from parrot.fixtures import FixtureBase
from tkinter import Canvas
from parrot.utils.color_extra import dim_color


HEAD_WIDTH = 20
HEAD_HEIGHT = 25

BASE_WIDTH = 40
BASE_HEIGHT = 10

LIGHT_RADIUS = 7

BEAM_RADIUS = 20


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
            outline="black",
        )
        self.head = canvas.create_rectangle(
            x + self.height / 2 - HEAD_WIDTH / 2,
            y,
            x + self.height / 2 + HEAD_WIDTH / 2,
            y + HEAD_HEIGHT,
            fill="black",
            outline="black",
        )

        self.light_cx = x + self.width / 2
        self.light_cy = y + 5 + LIGHT_RADIUS

        self.light = canvas.create_oval(
            x + self.width / 2 - LIGHT_RADIUS,
            y + 5,
            x + self.width / 2 + LIGHT_RADIUS,
            y + 5 + 2 * LIGHT_RADIUS,
            fill="black",
            outline="black",
        )

        self.beam = canvas.create_line(
            self.light_cx,
            self.light_cy,
            self.light_cx,
            self.light_cy,
            fill="black",
            width=3,
        )

    def render(self, canvas: Canvas, frame: Frame):
        color = self.fixture.get_color()
        dim = self.fixture.get_dimmer()

        canvas.itemconfig(self.light, fill=dim_color(color, dim / 255))

        if dim < 10:
            canvas.itemconfig(self.beam, fill="")
        else:
            canvas.itemconfig(self.beam, fill=dim_color(color, dim / 255))

        canvas.coords(
            self.beam,
            self.light_cx,
            self.light_cy,
            self.light_cx
            + BEAM_RADIUS * math.cos(self.fixture.get_pan_angle() / 180 * math.pi),
            self.light_cy
            + BEAM_RADIUS * math.sin(self.fixture.get_tilt_angle() / 180 * math.pi),
        )
