from parrot.director.frame import Frame
from .base import FixtureGuiRenderer
from parrot.fixtures import FixtureBase
from tkinter import Canvas
from parrot.utils.color_extra import dim_color

BULB_DIA = 8
BULB_MARGIN = 2
BULBS = 8


class MotionstripRenderer(FixtureGuiRenderer[FixtureBase]):
    def __init__(self, fixture: FixtureBase):
        super().__init__(fixture)

    @property
    def width(self) -> int:
        return BULB_MARGIN * 2 + BULB_MARGIN * (BULBS - 1) + BULB_DIA * BULBS

    @property
    def height(self) -> int:
        return BULB_MARGIN * 2 + BULB_DIA

    def setup(self, canvas: Canvas):
        self.shape = canvas.create_rectangle(
            self.x,
            self.y,
            self.x + self.width,
            self.y + self.height,
            fill="black",
            outline="black",
        )

        self.bulbs = []

        for i in range(BULBS):
            x_pos = self.x + BULB_MARGIN + (BULB_DIA + BULB_MARGIN) * i
            self.bulbs.append(
                canvas.create_oval(
                    x_pos,
                    self.y + BULB_MARGIN,
                    x_pos + BULB_DIA,
                    self.y + BULB_MARGIN + BULB_DIA,
                    fill="black",
                    outline="black",
                )
            )

    def set_position(self, canvas: Canvas, x: int, y: int):
        super().set_position(canvas, x, y)

        canvas.coords(
            self.shape,
            self.x,
            self.y,
            self.x + self.width,
            self.y + self.height,
        )

        for i, bulb in enumerate(self.bulbs):
            x_pos = self.x + BULB_MARGIN + (BULB_DIA + BULB_MARGIN) * i

            canvas.coords(
                bulb,
                x_pos,
                self.y + BULB_MARGIN,
                x_pos + BULB_DIA,
                self.y + BULB_MARGIN + BULB_DIA,
            )

    def render(self, canvas: Canvas, frame: Frame):
        color = self.fixture.get_color()
        dim = self.fixture.get_dimmer()

        # canvas.itemconfig(self.shape, fill=dim_color(color, dim / 255))

        for i, oval in enumerate(self.bulbs):
            bc = self.fixture.get_bulb_color(i)
            canvas.itemconfig(oval, fill=dim_color(bc, dim / 255))
