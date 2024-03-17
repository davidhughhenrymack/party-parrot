from tkinter import *

from parrot.state import State
from parrot.interpreters.base import Phrase
from parrot.patch_bay import patch_bay
from parrot.utils.color_extra import dim_color

CIRCLE_SIZE = 30
CIRCLE_GAP = 20


class Window(Tk):
    def __init__(self, state: State):
        super().__init__()
        self.state = state

        self.title("Party Parrot")

        self.canvas = Canvas(self, width=800, height=300)
        self.canvas.pack()

        self.fixture_circles = []

        for idx, fixture in enumerate(patch_bay):
            self.fixture_circles.append(
                self.canvas.create_oval(
                    idx * (CIRCLE_SIZE + CIRCLE_GAP) + CIRCLE_GAP,
                    CIRCLE_GAP,
                    idx * (CIRCLE_SIZE + CIRCLE_GAP) + CIRCLE_SIZE + CIRCLE_GAP,
                    CIRCLE_GAP + CIRCLE_SIZE,
                    fill="black",
                )
            )

        for i in Phrase:
            button = Button(text=i.name, command=lambda: self.state.set_phrase(i))
            button.pack()

        self.label_var = StringVar()
        self.label = Label(textvariable=self.label_var)
        self.label.pack()

    def step(self, frame):
        self.label_var.set("Sustained: {:.2f}".format(frame["sustained"]))

        for idx, fixture in enumerate(patch_bay):
            color = fixture.get_color()
            dim = fixture.get_dimmer()
            dimmed = dim_color(color, dim / 255)
            self.canvas.itemconfig(self.fixture_circles[idx], fill=dimmed.hex)
