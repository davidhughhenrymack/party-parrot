import math
from parrot.director.frame import Frame
from .base import FixtureGuiRenderer, render_strobe_dim_color
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

    def setup(self, canvas: Canvas):
        self.base = canvas.create_rectangle(
            self.x,
            self.y + self.height - BASE_HEIGHT,
            self.x + self.width,
            self.y + self.height,
            fill="black",
            outline="black",
        )
        self.head = canvas.create_rectangle(
            self.x + self.height / 2 - HEAD_WIDTH / 2,
            self.y,
            self.x + self.height / 2 + HEAD_WIDTH / 2,
            self.y + HEAD_HEIGHT,
            fill="black",
            outline="black",
        )

        self.light_cx = self.x + self.width / 2
        self.light_cy = self.y + 5 + LIGHT_RADIUS

        self.light = canvas.create_oval(
            self.x + self.width / 2 - LIGHT_RADIUS,
            self.y + 5,
            self.x + self.width / 2 + LIGHT_RADIUS,
            self.y + 5 + 2 * LIGHT_RADIUS,
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

        # Call parent setup to create DMX address label
        super().setup(canvas)

    def set_position(self, canvas: Canvas, x: int, y: int):
        super().set_position(canvas, x, y)

        canvas.coords(
            self.base,
            self.x,
            self.y + self.height - BASE_HEIGHT,
            self.x + self.width,
            self.y + self.height,
        )
        canvas.coords(
            self.head,
            self.x + self.height / 2 - HEAD_WIDTH / 2,
            self.y,
            self.x + self.height / 2 + HEAD_WIDTH / 2,
            self.y + HEAD_HEIGHT,
        )

        self.light_cx = self.x + self.width / 2
        self.light_cy = self.y + 5 + LIGHT_RADIUS

        canvas.coords(
            self.light,
            self.x + self.width / 2 - LIGHT_RADIUS,
            self.y + 5,
            self.x + self.width / 2 + LIGHT_RADIUS,
            self.y + 5 + 2 * LIGHT_RADIUS,
        )

        canvas.coords(
            self.beam,
            self.light_cx,
            self.light_cy,
            self.light_cx,
            self.light_cy,
        )

    def render(self, canvas: Canvas, frame: Frame):
        fill = render_strobe_dim_color(self.fixture, frame)
        canvas.itemconfig(self.light, fill=fill)

        if fill.get_luminance() < 0.1:
            canvas.itemconfig(self.beam, fill="")
        else:
            canvas.itemconfig(self.beam, fill=fill)

        canvas.coords(
            self.beam,
            self.light_cx,
            self.light_cy,
            self.light_cx
            + BEAM_RADIUS * math.cos(self.fixture.get_pan_angle() / 180 * math.pi),
            self.light_cy
            + BEAM_RADIUS * math.sin(self.fixture.get_tilt_angle() / 180 * math.pi),
        )
