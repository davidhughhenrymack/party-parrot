import json
import os
from tkinter import *
from tkinter.ttk import Combobox

from parrot.director.director import Director
import parrot.director.frame
from parrot.director.frame import Frame as DirectorFrame
from parrot.state import State
from parrot.director.phrase import Phrase
from parrot.patch_bay import venue_patches, venues, get_manual_group
from parrot.director.themes import themes
from parrot.fixtures.base import ManualGroup
from .fixtures.factory import renderer_for_fixture
from .fixtures.group import FixtureGroupRenderer
from parrot.utils.math import distance

CIRCLE_SIZE = 30
FIXTURE_MARGIN = 20

BG = "#222"

CANVAS_WIDTH = 800

SHOW_PLOT = os.environ.get("HIDE_PLOT", "false") != "true"


class Window(Tk):
    def __init__(self, state: State, quit: callable, director: Director):
        super().__init__()

        self.state = state
        # state.events.on_phrase_change += lambda phrase: self.on_phrase_change(phrase)

        self.title("Party Parrot")
        # set background color to black
        self.configure(bg=BG)
        self.protocol("WM_DELETE_WINDOW", quit)

        self.top_frame = Frame(self, background=BG)

        self.venue_select = Combobox(
            self.top_frame, values=[i.name for i in venues], state="readonly"
        )
        self.venue_select.current([i for i in venues].index(state.venue))
        self.venue_select.bind(
            "<<ComboboxSelected>>",
            lambda e: state.set_venue([i for i in venues][self.venue_select.current()]),
        )
        self.venue_select.pack(side=LEFT, padx=5, pady=5)

        self.theme_select = Combobox(
            self.top_frame, values=[i.name for i in themes], state="readonly"
        )
        # Set the current theme based on the state
        current_theme_index = themes.index(state.theme)
        self.theme_select.current(current_theme_index)
        self.theme_select.bind(
            "<<ComboboxSelected>>",
            lambda e: state.set_theme(themes[self.theme_select.current()]),
        )
        self.theme_select.pack(side=LEFT, padx=5, pady=5)

        self.top_frame.pack()

        # Create a frame for the main content with canvas and manual control
        self.main_content_frame = Frame(self, background=BG)

        # Create a frame for manual control
        self.manual_control_frame = Frame(self.main_content_frame, background=BG)

        # Create vertical slider for manual control
        self.manual_slider = Scale(
            self.manual_control_frame,
            from_=100,
            to=0,
            length=400,
            orient=VERTICAL,
            bg=BG,
            fg="white",
            highlightbackground=BG,
            troughcolor="#444",
            label="",
            command=self.update_manual_dimmer,
        )
        self.manual_slider.set(int(self.state.manual_dimmer * 100))
        self.manual_slider.pack(padx=10, pady=10, fill=Y, expand=True)

        # Only show manual control if there is a manual group for this venue
        if get_manual_group(self.state.venue):
            self.manual_control_frame.pack(side=RIGHT, fill=Y)

        # Add event handler for venue change to show/hide manual control
        self.state.events.on_venue_change += self.update_manual_control_visibility

        self.canvas = Canvas(
            self.main_content_frame,
            width=CANVAS_WIDTH,
            height=800,
            bg=BG,
            borderwidth=0,
            selectborderwidth=0,
        )
        self.canvas.pack(side=LEFT)

        self.main_content_frame.pack()

        self._drag_data = {"x": 0, "y": 0, "item": None}
        self.canvas.bind("<ButtonPress-1>", self.drag_start)
        self.canvas.bind("<ButtonRelease-1>", self.drag_stop)
        self.canvas.bind("<B1-Motion>", self.drag)

        self.setup_patch()
        self.state.events.on_venue_change += lambda x: self.setup_patch()

        # self.phrase_frame = Frame(self, background=BG)

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

        self.btn_frame = Frame(self, background=BG)

        self.deploy_hype = Button(
            self.btn_frame,
            text="HYPE!!",
            command=lambda: director.deploy_hype(),
            highlightbackground=BG,
            height=2,
        )
        self.deploy_hype.pack(side=LEFT, padx=5, pady=5)

        self.shift = Button(
            self.btn_frame,
            text="Shift",
            command=lambda: director.shift(),
            highlightbackground=BG,
            height=2,
        )
        self.shift.pack(side=LEFT, padx=5, pady=5)
        self.btn_frame.pack()

        if SHOW_PLOT:
            self.graph = Canvas(self, width=CANVAS_WIDTH, height=100, bg=BG)
            self.graph.pack()

    def setup_patch(self):
        self.canvas.delete("all")

        # Create renderers for all fixtures
        self.fixture_renderers = [
            renderer_for_fixture(fixture) for fixture in venue_patches[self.state.venue]
        ]

        # Set up all renderers
        for renderer in self.fixture_renderers:
            renderer.setup(self.canvas)

        # Position renderers, with each group on its own row
        fixture_x = FIXTURE_MARGIN
        fixture_y = FIXTURE_MARGIN

        for idx, renderer in enumerate(self.fixture_renderers):
            # Check if we need to start a new row
            if fixture_x + renderer.width + FIXTURE_MARGIN > CANVAS_WIDTH:
                fixture_x = FIXTURE_MARGIN
                fixture_y += 100

            # Position the renderer
            renderer.set_position(self.canvas, fixture_x, fixture_y)

            # Move to the next position
            fixture_x += renderer.width + FIXTURE_MARGIN

            # If this is a group renderer or the last renderer, start a new row for the next renderer
            if (
                isinstance(renderer, FixtureGroupRenderer)
                or idx == len(self.fixture_renderers) - 1
            ):
                fixture_x = FIXTURE_MARGIN
                fixture_y += 100

        self.load()

    def on_key_press(self, event):
        self.state.set_phrase(Phrase.build)

    def drag_start(self, event):
        """Beginning drag of an object"""
        # record the item and its location
        self._drag_data["item"] = None
        closest = 999999999

        # Create a flat list of all renderers, including those inside groups
        all_renderers = []
        for renderer in self.fixture_renderers:
            if isinstance(renderer, FixtureGroupRenderer):
                # Add individual fixtures from the group
                all_renderers.extend(renderer.fixture_renderers)
            else:
                all_renderers.append(renderer)

        # Find the closest renderer to the click point
        for renderer in all_renderers:
            dist = distance(event.x, renderer.x, event.y, renderer.y)
            if dist < closest and dist < 100:
                self._drag_data["item"] = renderer
                closest = dist

        # Set the starting position for the drag
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
        # Check if we have a valid item to drag
        if self._drag_data["item"] is None:
            return

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

    def step(self, frame: parrot.director.frame.Frame):
        for renderer in self.fixture_renderers:
            renderer.render(self.canvas, frame)

        if SHOW_PLOT:
            self.step_plot(frame)

    def step_plot(self, frame):
        self.graph.delete("all")
        g_height = self.graph.winfo_height()

        for idx, (name, values) in enumerate(frame.timeseries.items()):
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
        filename = f"{self.state.venue.name}_gui.json"

        # Save all renderers, including those inside groups
        for renderer in self.fixture_renderers:
            if isinstance(renderer, FixtureGroupRenderer):
                # Save individual fixtures from the group
                for fixture_renderer in renderer.fixture_renderers:
                    data[fixture_renderer.fixture.id] = fixture_renderer.to_json()
            else:
                data[renderer.fixture.id] = renderer.to_json()

        # write to file
        with open(filename, "w") as f:
            json.dump(data, f, indent=4)

    def load(self):
        filename = f"{self.state.venue.name}_gui.json"
        # read from file
        if not os.path.exists(filename):
            return

        with open(filename, "r") as f:
            data = json.load(f)

        # load json for all renderers, including those inside groups
        for renderer in self.fixture_renderers:
            if isinstance(renderer, FixtureGroupRenderer):
                # Load individual fixtures from the group
                for fixture_renderer in renderer.fixture_renderers:
                    if fixture_renderer.fixture.id in data:
                        fixture_renderer.from_json(
                            self.canvas, data[fixture_renderer.fixture.id]
                        )
            else:
                if renderer.fixture.id in data:
                    renderer.from_json(self.canvas, data[renderer.fixture.id])

    def update_manual_control_visibility(self, venue):
        """Show or hide manual control based on whether there is a manual group for this venue."""
        if get_manual_group(venue):
            self.manual_control_frame.pack(side=RIGHT, fill=Y)
        else:
            self.manual_control_frame.pack_forget()

    def update_manual_dimmer(self, val):
        """Update the manual dimmer value and refresh the GUI."""
        dimmer_value = float(val) / 100
        self.state.set_manual_dimmer(dimmer_value)

        # Force an immediate update of the manual fixtures in the GUI
        manual_group = get_manual_group(self.state.venue)
        if manual_group:
            # Update the manual group's dimmer value
            manual_group.set_manual_dimmer(dimmer_value)

            # Find the manual group renderer and update it
            for renderer in self.fixture_renderers:
                if isinstance(renderer.fixture, ManualGroup):
                    # Create an empty frame with default values
                    empty_frame = DirectorFrame({})
                    # Force a render update for the manual group
                    renderer.render(self.canvas, empty_frame)
                    break
