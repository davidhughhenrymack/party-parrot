from .base import FixtureGuiRenderer
from parrot.fixtures import FixtureBase
from tkinter import Canvas
from parrot.utils.color_extra import dim_color

BULB_DIA = 5
BULB_MARGIN = 3
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

    def setup(self, canvas: Canvas, x: int, y: int):
        self.shape = canvas.create_rectangle(
            x,
            y,
            x + self.width,
            y + self.height,
            fill="black",
        )

        self.bulbs = []

        for i in range(BULBS):
            x_pos = x + BULB_MARGIN + (BULB_DIA + BULB_MARGIN) * i
            self.bulbs.append(
                canvas.create_oval(
                    x_pos,
                    y + BULB_MARGIN,
                    x_pos + BULB_DIA,
                    y + BULB_MARGIN + BULB_DIA,
                    fill="black",
                )
            )

    def render(self, canvas: Canvas):
        color = self.fixture.get_color()
        dim = self.fixture.get_dimmer()

        # canvas.itemconfig(self.shape, fill=dim_color(color, dim / 255))

        for i, oval in enumerate(self.bulbs):
            bc = self.fixture.get_bulb_color(i)
            canvas.itemconfig(oval, fill=dim_color(bc, dim / 255))
