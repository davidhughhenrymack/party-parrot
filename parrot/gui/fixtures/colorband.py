from parrot.director.frame import Frame
from .base import FixtureGuiRenderer
from parrot.fixtures.chauvet.colorband_pix import ChauvetColorBandPiX_36Ch
from tkinter import Canvas
from parrot.utils.color_extra import dim_color

BULB_DIA = 8
BULB_MARGIN = 2
ZONES = 12  # ColorBand has 12 zones


class ColorBandRenderer(FixtureGuiRenderer[ChauvetColorBandPiX_36Ch]):
    def __init__(self, fixture: ChauvetColorBandPiX_36Ch):
        super().__init__(fixture)

    @property
    def width(self) -> int:
        return BULB_MARGIN * 2 + BULB_MARGIN * (ZONES - 1) + BULB_DIA * ZONES

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

        for i in range(ZONES):
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

        for i, (oval, zone) in enumerate(zip(self.bulbs, self.fixture.get_zones())):
            zc = zone.get_color()
            zc = dim_color(zc, zone.get_dimmer() / 255)
            canvas.itemconfig(oval, fill=dim_color(zc, dim / 255))
