from tkinter import *

from parrot.state import State
from parrot.interpreters.base import Phrase
from parrot.patch_bay import patch_bay
from parrot.utils.color_extra import dim_color
from .fixtures.factory import renderer_for_fixture

CIRCLE_SIZE = 30
FIXTURE_MARGIN = 20

BG = "#222"

CANVAS_WIDTH = 500


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
            width=CANVAS_WIDTH,
            height=400,
            bg=BG,
            borderwidth=0,
            border=0,
            selectborderwidth=0,
        )
        self.canvas.pack()

        self.bind("<space>", lambda e: self.state.set_phrase(Phrase.drop))
        self.bind("<Key>", self.on_key_press)
        self.fixture_renderers = [
            renderer_for_fixture(fixture) for fixture in patch_bay
        ]

        fixture_x = FIXTURE_MARGIN
        fixture_y = FIXTURE_MARGIN
        for idx, renderer in enumerate(self.fixture_renderers):
            if fixture_x + renderer.width + FIXTURE_MARGIN > CANVAS_WIDTH:
                fixture_x = FIXTURE_MARGIN
                fixture_y += 100
            renderer.setup(self.canvas, fixture_x, fixture_y)
            fixture_x += renderer.width + FIXTURE_MARGIN

        self.phrase_frame = Frame(self, background=BG)

        self.phrase_buttons = {}
        for i in Phrase:
            self.phrase_buttons[i] = Button(
                self.phrase_frame,
                text=i.name,
                command=lambda i=i: self.click_phrase(i),
                highlightbackground=BG,
            )
            self.phrase_buttons[i].pack(side=LEFT, padx=5, pady=5)

        self.phrase_frame.pack()

        self.label_var = StringVar()
        self.label = Label(self, textvariable=self.label_var, bg=BG, fg="white")
        self.label.pack()

        state.events.on_phrase_change += lambda phrase: self.on_phrase_change(phrase)

    def click_phrase(self, phrase: Phrase):
        self.state.set_phrase(phrase)

    def on_phrase_change(self, phrase: Phrase):
        for phrase, button in self.phrase_buttons.items():
            if phrase == self.state.phrase:
                button.config(highlightbackground="green")
            else:
                button.config(highlightbackground=BG)

    def on_key_press(self, event):
        self.state.set_phrase(Phrase.build)

    def step(self, frame):
        self.label_var.set(
            "All: {:.2f}, Sustained: {:.2f}, Drums: {:.2f}".format(
                frame["all"], frame["sustained"], frame["drums"]
            )
        )

        for renderer in self.fixture_renderers:
            renderer.render(self.canvas, frame)
