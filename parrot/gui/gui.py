from tkinter import *

from parrot.state import State
from parrot.interpreters.base import Phrase


class Window(Tk):
    def __init__(self, state: State):
        super().__init__()
        self.state = state

        self.title("Party Parrot")

        for i in Phrase:
            button = Button(text=i.name, command=lambda: self.state.set_phrase(i))
            button.pack()

        self.label_var = StringVar()
        self.label = Label(textvariable=self.label_var)
        self.label.pack()

    def step(self, frame):
        self.label_var.set("Sustained: {:.2f}".format(frame["sustained"]))
