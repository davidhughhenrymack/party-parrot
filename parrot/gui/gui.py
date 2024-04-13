import json
import os
from tkinter import *
from tkinter.ttk import Combobox

from parrot.director.frame import FrameSignal
from parrot.state import State
from parrot.director.phrase import Phrase
from parrot.patch_bay import patch_bay
from parrot.director.themes import themes
from .fixtures.factory import renderer_for_fixture
from parrot.utils.math import distance

CIRCLE_SIZE = 30
FIXTURE_MARGIN = 20

BG = "#222"

CANVAS_WIDTH = 500


class Window(Tk):
    def __init__(self, state: State, quit: callable):
        super().__init__()

        self.state = state
        # state.events.on_phrase_change += lambda phrase: self.on_phrase_change(phrase)

        self.title("Party Parrot")
        # set background color to black
        self.configure(bg=BG)
        self.protocol("WM_DELETE_WINDOW", quit)

        self.theme_select = Combobox(
            self, values=[i.name for i in themes], state="readonly"
        )
        self.theme_select.current(0)
        self.theme_select.bind(
            "<<ComboboxSelected>>",
            lambda e: state.set_theme(themes[self.theme_select.current()]),
        )
        self.theme_select.pack()

        self.canvas = Canvas(
            self,
            width=CANVAS_WIDTH,
            height=400,
            bg=BG,
            borderwidth=0,
            selectborderwidth=0,
        )
        self.canvas.pack()
        self._drag_data = {"x": 0, "y": 0, "item": None}
        self.canvas.bind("<ButtonPress-1>", self.drag_start)
        self.canvas.bind("<ButtonRelease-1>", self.drag_stop)
        self.canvas.bind("<B1-Motion>", self.drag)

        # self.bind("<space>", lambda e: self.state.set_phrase(Phrase.drop))
        # self.bind("<Key>", self.on_key_press)
        self.fixture_renderers = [
            renderer_for_fixture(fixture) for fixture in patch_bay
        ]

        fixture_x = FIXTURE_MARGIN
        fixture_y = FIXTURE_MARGIN
        for idx, renderer in enumerate(self.fixture_renderers):
            if fixture_x + renderer.width + FIXTURE_MARGIN > CANVAS_WIDTH:
                fixture_x = FIXTURE_MARGIN
                fixture_y += 100
            renderer.setup(self.canvas)
            renderer.set_position(self.canvas, fixture_x, fixture_y)
            fixture_x += renderer.width + FIXTURE_MARGIN

        self.load()

        self.phrase_frame = Frame(self, background=BG)

        # self.phrase_buttons = {}
        # for i in Phrase:
        #     self.phrase_buttons[i] = Button(
        #         self.phrase_frame,
        #         text=i.name,
        #         command=lambda i=i: self.state.set_phrase(i),
        #         highlightbackground=BG,
        #         height=3,
        #     )
        #     self.phrase_buttons[i].pack(side=LEFT, padx=5, pady=5)

        # self.phrase_frame.pack()

        self.label_var = StringVar()
        self.label = Label(self, textvariable=self.label_var, bg=BG, fg="white")
        # self.label.pack()

        self.scale = Scale(
            self, from_=0, to=100, length=CANVAS_WIDTH, orient=HORIZONTAL
        )
        self.scale.set(self.state.hype)
        self.scale.bind(
            "<ButtonRelease-1>", lambda e: self.state.set_hype(self.scale.get())
        )
        self.scale.pack()

        self.graph = Canvas(self, width=CANVAS_WIDTH, height=100, bg=BG)
        self.graph.pack()

    # def on_phrase_change(self, phrase: Phrase):
    #     for phrase, button in self.phrase_buttons.items():
    #         if phrase == self.state.phrase:
    #             button.config(highlightbackground="green")
    #         else:
    #             button.config(highlightbackground=BG)

    def on_key_press(self, event):
        self.state.set_phrase(Phrase.build)

    def drag_start(self, event):
        """Begining drag of an object"""
        # record the item and its location
        self._drag_data["item"] = None
        closest = 999999999
        for i in self.fixture_renderers:
            dist = distance(event.x, i.x, event.y, i.y)
            if dist < closest and dist < 100:
                self._drag_data["item"] = i
                closest = dist

        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def drag_stop(self, event):
        """End drag of an object"""
        # reset the drag information
        self._drag_data["item"] = None
        self._drag_data["x"] = 0
        self._drag_data["y"] = 0
        self.save()

    def drag(self, event):
        """Handle dragging of an object"""
        # compute how much the mouse has moved
        delta_x = event.x - self._drag_data["x"]
        delta_y = event.y - self._drag_data["y"]
        # move the object the appropriate amount
        self._drag_data["item"].set_position(
            self.canvas,
            self._drag_data["item"].x + delta_x,
            self._drag_data["item"].y + delta_y,
        )
        # record the new position
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def step(self, frame):
        for renderer in self.fixture_renderers:
            renderer.render(self.canvas, frame)

        self.graph.delete("all")
        g_height = self.graph.winfo_height()

        for idx, (name, values) in enumerate(frame.plot.items()):
            if len(values) == 0:
                continue

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
                y0 = g_height - values[i - 1] * g_height
                x1 = i * x_scale
                y1 = g_height - value * g_height
                self.graph.create_line(
                    x0,
                    y0,
                    x1,
                    y1,
                    fill=fill,
                )

    def save(self):
        data = {}
        for i in self.fixture_renderers:
            data[i.fixture.id] = i.to_json()

        # write to file
        with open("gui.json", "w") as f:
            json.dump(data, f, indent=4)

    def load(self):
        # read from file
        if not os.path.exists("gui.json"):
            return

        with open("gui.json", "r") as f:
            data = json.load(f)
        # load json
        for i in self.fixture_renderers:
            if i.fixture.id in data:
                i.from_json(self.canvas, data[i.fixture.id])
