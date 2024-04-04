import math
import scipy
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
        state.events.on_phrase_change += lambda phrase: self.on_phrase_change(phrase)

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
                height=7,
            )
            self.phrase_buttons[i].pack(side=LEFT, padx=5, pady=5)

        self.phrase_frame.pack()

        self.label_var = StringVar()
        self.label = Label(self, textvariable=self.label_var, bg=BG, fg="white")
        # self.label.pack()

        self.graph = Canvas(self, width=CANVAS_WIDTH, height=200, bg=BG)
        self.graph.pack()

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
        # self.label_var.set(
        #     "All: {:.2f}, Sustained: {:.2f}, Drums: {:.2f}, Build rate: {:.2f}".format(
        #         frame["all"], frame["sustained"], frame["drums"], frame["build_rate"]
        #     )
        # )

        for renderer in self.fixture_renderers:
            renderer.render(self.canvas, frame)

        self.graph.delete("all")
        for idx, (name, values) in enumerate(frame.plot.items()):
            if len(values) == 0:
                continue
            # find max and min values
            # min_value = min(values)
            # max_value = max(values)

            fill = ["red", "green", "blue", "purple", "orange"][idx]

            self.graph.create_text(
                40, 10 + idx * 20, text=name, fill=fill, justify="left"
            )

            # Normalize values
            # values = [
            #     (i - min_value) / (max_value - min_value + 0.000001) for i in values
            # ]

            x_scale = CANVAS_WIDTH / len(values)

            # For each value in values draw line segment from previous value to current value
            for i, value in enumerate(values):
                if i == 0:
                    continue
                x0 = (i - 1) * x_scale
                y0 = 200 - values[i - 1] * 200
                x1 = i * x_scale
                y1 = 200 - value * 200
                self.graph.create_line(
                    x0,
                    y0,
                    x1,
                    y1,
                    fill=fill,
                )
