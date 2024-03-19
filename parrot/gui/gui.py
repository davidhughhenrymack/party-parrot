from tkinter import *

from parrot.state import State
from parrot.interpreters.base import Phrase
from parrot.patch_bay import patch_bay
from parrot.utils.color_extra import dim_color
from .fixtures.factory import renderer_for_fixture

CIRCLE_SIZE = 30
FIXTURE_MARGIN = 20

BG = "#222"


class Window(Tk):
    def __init__(self, state: State, quit: callable):
        super().__init__()
        self.state = state

        self.title("Party Parrot")
        # set background color to black
        self.configure(bg=BG)
        self.protocol("WM_DELETE_WINDOW", quit)

        self.canvas = Canvas(
            self,
            width=500,
            height=100,
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

        self.phrase_frame = Frame(self, background=BG)

        self.phrase_buttons = {}
        for i in Phrase:
            self.phrase_buttons[i] = Button(
                self.phrase_frame,
                text=i.name,
                command=lambda i=i: self.click_phrase(i),
            )
            self.phrase_buttons[i].pack(side=LEFT, padx=5, pady=5)

        self.click_phrase(self.state.phrase)

        self.phrase_frame.pack()

    def click_phrase(self, phrase: Phrase):
        self.state.set_phrase(phrase)
        for phrase, button in self.phrase_buttons.items():
            if phrase.value == self.state.phrase.value:
                button.config(relief="sunken", background="green")
            else:
                button.config(relief="raised")

    def step(self, frame):
        # self.label_var.set("Sustained: {:.2f}".format(frame["sustained"]))

        for renderer in self.fixture_renderers:
            renderer.render(self.canvas)
