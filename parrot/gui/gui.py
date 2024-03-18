from tkinter import *

from parrot.state import State
from parrot.interpreters.base import Phrase
from parrot.patch_bay import patch_bay
from parrot.utils.color_extra import dim_color
from .fixtures.factory import renderer_for_fixture

CIRCLE_SIZE = 30
FIXTURE_MARGIN = 20

BG = "#111"


class Window(Tk):
    def __init__(self, state: State):
        super().__init__()
        self.state = state

        self.title("Party Parrot")
        # set background color to black
        self.configure(bg=BG)

        self.canvas = Canvas(
            self,
            width=800,
            height=300,
            bg=BG,
            borderwidth=0,
            border=0,
            selectborderwidth=0,
        )
        self.canvas.pack()

        self.fixture_renderers = [
            renderer_for_fixture(fixture) for fixture in patch_bay
        ]

        fixture_x = FIXTURE_MARGIN
        fixture_y = FIXTURE_MARGIN
        for idx, renderer in enumerate(self.fixture_renderers):
            renderer.setup(self.canvas, fixture_x, fixture_y)
            fixture_x += renderer.width + FIXTURE_MARGIN

        for i in Phrase:
            button = Button(text=i.name, command=lambda: self.state.set_phrase(i))
            button.pack()

        self.label_var = StringVar()
        self.label = Label(textvariable=self.label_var)
        self.label.pack()

    def step(self, frame):
        self.label_var.set("Sustained: {:.2f}".format(frame["sustained"]))

        for renderer in self.fixture_renderers:
            renderer.render(self.canvas)
