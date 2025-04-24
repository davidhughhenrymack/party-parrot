import json
import os
from tkinter import (
    Tk,
    Frame,
    Canvas,
    Button,
    Scale,
    Label,
    StringVar,
    LEFT,
    RIGHT,
    BOTH,
    VERTICAL,
    HORIZONTAL,
    Y,
    X,
    TOP,
    BOTTOM,
    NW,
    SE,
    Listbox,
    Toplevel,
    Radiobutton,
    RAISED,
    SUNKEN,
    FLAT,
    GROOVE,
    RIDGE,
    SOLID,
)

from parrot.director.director import Director
import parrot.director.frame
from parrot.director.frame import Frame as DirectorFrame, FrameSignal
from parrot.state import State
from parrot.director.mode import Mode
from parrot.patch_bay import venue_patches, venues, get_manual_group, has_manual_dimmer
from parrot.director.themes import themes
from parrot.fixtures.base import FixtureGroup, ManualGroup
from .fixtures.factory import renderer_for_fixture
from parrot.utils.math import distance
import sys
from parrot.director.signal_states import SignalStates

CIRCLE_SIZE = 30
FIXTURE_MARGIN = 10

BG = "#222"
FG = "#d0d0d0"  # Light text color
ENTRY_BG = "#333"  # Slightly darker than BG for text entry
ENTRY_FG = "#d0d0d0"  # Same as FG
BUTTON_BG = "#ddd"  # Same as BG for a seamless look
BUTTON_FG = "#000"
BUTTON_BORDER = "#8a2be2"  # Purple border
BUTTON_ACTIVE_BG = "#333"  # Slightly lighter than button bg
BUTTON_ACTIVE_FG = "#8a2be2"  # Purple text on press
HIGHLIGHT_COLOR = "#0078d7"
CANVAS_WIDTH = 1200
CANVAS_HEIGHT = 800
SHOW_PLOT = os.environ.get("HIDE_PLOT", "false") != "true"

# Selection box color
SELECTION_BOX_COLOR = "#aaaaff"
SELECTION_BOX_ALPHA = 30  # Transparency level (0-255)

# Selection outline properties
SELECTION_OUTLINE_COLOR = "white"
SELECTION_OUTLINE_WIDTH = 2
DEFAULT_OUTLINE_COLOR = "black"
DEFAULT_OUTLINE_WIDTH = 1


class RoundedButton(Button):
    """A custom button with rounded corners and hover effects."""

    def __init__(
        self,
        master=None,
        release_command=lambda: None,
        press_command=lambda: None,
        **kwargs,
    ):
        # Apply default button style if not overridden
        button_style = {
            "background": BUTTON_BG,
            "foreground": BUTTON_FG,
            "activebackground": BUTTON_ACTIVE_BG,
            "activeforeground": BUTTON_ACTIVE_FG,
            "highlightbackground": BUTTON_BG,  # Same as background to hide border
            "highlightcolor": BUTTON_BORDER,  # For hover effect
            "borderwidth": 0,  # No border
            "relief": "flat",  # No bevel
            "font": ("calibri", 10, "bold"),
            "highlightthickness": 2,  # Increased for better visibility
            "padx": 10,
            "pady": 5,
        }

        # Update with any provided kwargs
        button_style.update(kwargs)

        super().__init__(master, **button_style)

        # Store original colors
        self.original_bg = button_style["background"]
        self.original_fg = button_style["foreground"]
        self.original_highlight_bg = button_style["highlightbackground"]

        # Bind events for hover and press effects
        self.bind("<Enter>", self.on_enter)
        self.bind("<Leave>", self.on_leave)
        self.bind("<ButtonPress-1>", self.on_press)
        self.bind("<ButtonRelease-1>", self.on_release)

        self.release_command = release_command
        self.press_command = press_command

    def on_enter(self, event):
        """Change border color on hover."""
        # Don't change the background - we want to preserve custom colors
        pass

    def on_leave(self, event):
        """Reset border color when mouse leaves."""
        # Don't change the background - we want to preserve custom colors
        pass

    def on_press(self, event):
        """Change text color when button is pressed."""
        # Store the current colors before changing them
        self.original_bg = self.cget("background")
        self.original_fg = self.cget("foreground")
        self.original_highlight_bg = self.cget("highlightbackground")

        # Use activebackground for press effect
        self.config(
            foreground=BUTTON_ACTIVE_FG,
            background=self.cget("activebackground"),
        )
        self.press_command()

    def on_release(self, event):
        """Reset text color when button is released."""
        # Restore the original colors
        self.config(
            foreground=self.original_fg,
            background=self.original_bg,
            highlightbackground=self.original_highlight_bg,
        )
        self.release_command()


class NonBlockingDropdown:
    """A custom dropdown that doesn't block the main thread when open."""

    def __init__(self, parent, values, current_index=0, command=None, width=20):
        self.parent = parent
        self.values = values
        self.current_index = current_index
        self.command = command
        self.width = width
        self.popup = None
        self.is_open = False

        # Create button that looks like a dropdown
        self.button = Button(
            parent,
            text=self.values[current_index] + " ▼",  # Add caret icon
            command=self.show_dropdown,
            width=width,
            background=BUTTON_BG,
            foreground=BUTTON_FG,
            activebackground=BUTTON_ACTIVE_BG,
            activeforeground=BUTTON_ACTIVE_FG,
            relief=FLAT,
            borderwidth=1,
            highlightthickness=0,
        )

    def show_dropdown(self):
        # If popup is already open, close it
        if self.popup:
            self.close_dropdown()
            return

        # Change button style when dropdown is open
        self.is_open = True
        self.button.config(background=BUTTON_ACTIVE_BG, foreground=BUTTON_ACTIVE_FG)

        # Create popup window
        self.popup = Toplevel(self.parent)
        self.popup.overrideredirect(True)  # Remove window decorations
        self.popup.transient(self.parent)  # Make it transient to parent

        # Position popup below button
        x = self.button.winfo_rootx()
        y = self.button.winfo_rooty() + self.button.winfo_height()
        self.popup.geometry(
            f"{self.button.winfo_width()}x{len(self.values)*20}+{x}+{y}"
        )

        # Create listbox with values
        self.listbox = Listbox(
            self.popup,
            bg=BUTTON_BG,
            fg=BUTTON_FG,
            selectbackground=HIGHLIGHT_COLOR,
            selectforeground="white",
            borderwidth=0,
            highlightthickness=0,
        )
        for value in self.values:
            self.listbox.insert("end", value)
        self.listbox.select_set(self.current_index)
        self.listbox.bind("<ButtonRelease-1>", self.on_select)
        self.listbox.pack(fill=BOTH, expand=True)

        # Close dropdown when focus is lost
        self.popup.bind("<FocusOut>", lambda e: self.after_idle(self.close_dropdown))
        self.popup.focus_set()

        # Ensure the main window keeps updating
        self.parent.update_idletasks()

    def close_dropdown(self):
        if self.popup:
            # Reset button style when dropdown is closed
            self.is_open = False
            self.button.config(background=BUTTON_BG, foreground=BUTTON_FG)
            self.popup.destroy()
            self.popup = None

    def on_select(self, event):
        if self.listbox.curselection():
            self.current_index = self.listbox.curselection()[0]
            self.button.config(
                text=self.values[self.current_index] + " ▼"
            )  # Keep caret icon
            self.close_dropdown()
            if self.command:
                # Use after_idle to avoid blocking
                self.parent.after_idle(lambda: self.command(self.current_index))

    def pack(self, **kwargs):
        self.button.pack(**kwargs)

    def current(self, index=None):
        if index is not None:
            self.current_index = index
            self.button.config(
                text=self.values[self.current_index] + " ▼"
            )  # Keep caret icon
        return self.current_index

    def after_idle(self, callback):
        """Schedule a callback to run in the idle loop."""
        self.parent.after_idle(callback)


class Window(Tk):
    def __init__(
        self,
        state: State,
        quit: callable,
        director: Director,
        signal_states: SignalStates,
    ):
        super().__init__()

        self.state = state
        self.director = director
        self.signal_states = signal_states
        state.events.on_mode_change += self.on_mode_change

        self.title("Party Parrot")
        # set background color to black
        self.configure(bg=BG)
        self.protocol("WM_DELETE_WINDOW", quit)

        self.option_add("*Frame.Background", BG)
        self.option_add("*Frame.borderWidth", 0)

        self.option_add("*Scale.Background", BG)
        self.option_add("*Scale.Foreground", BUTTON_FG)
        self.option_add("*Scale.activeBackground", BUTTON_ACTIVE_BG)
        self.option_add("*Scale.troughColor", BUTTON_BG)
        self.option_add("*Scale.highlightBackground", BG)
        self.option_add("*Scale.highlightThickness", 0)

        self.option_add("*Label.Background", BG)
        self.option_add("*Label.Foreground", BUTTON_FG)

        self.option_add("*Listbox.Background", BUTTON_BG)
        self.option_add("*Listbox.Foreground", BUTTON_FG)
        self.option_add("*Listbox.selectBackground", HIGHLIGHT_COLOR)
        self.option_add("*Listbox.selectForeground", BUTTON_FG)
        self.option_add("*Listbox.borderWidth", 0)
        self.option_add("*Listbox.highlightThickness", 0)

        self.option_add("*Canvas.highlightThickness", 0)
        self.option_add("*Canvas.borderWidth", 0)

        self.top_frame = Frame(self, background=BG)

        # Create a frame for mode selection radio buttons
        self.mode_frame = Frame(self.top_frame, background=BG)

        # Create a variable to track the selected mode
        # Handle the case when state.mode is None
        default_mode = state.mode.name if state.mode else ""
        self.mode_var = StringVar(value=default_mode)

        # Flag to track if mode change was initiated locally
        self.local_mode_change = False

        # Store mode buttons for later reference
        self.mode_buttons = {}

        # Create buttons for each mode instead of radio buttons
        for mode in Mode:
            btn = RoundedButton(
                self.mode_frame,
                text=mode.name.capitalize(),
                command=lambda mode=mode: self._select_mode(mode),
                background=BG,
                foreground=(
                    HIGHLIGHT_COLOR if mode.name == default_mode else BUTTON_FG
                ),
                activebackground=BUTTON_ACTIVE_BG,
                activeforeground=BUTTON_ACTIVE_FG,
                highlightthickness=1,
                highlightbackground=(
                    HIGHLIGHT_COLOR if mode.name == default_mode else BG
                ),
                borderwidth=1,
                relief=FLAT,
                padx=10,
                pady=4,
                width=8,
            )
            btn.pack(side=LEFT, padx=2)
            self.mode_buttons[mode.name] = btn

        # Pack the mode frame on the left side of the top frame
        self.mode_frame.pack(side=LEFT, padx=10, pady=5)

        # Add a status label to show web app changes
        self.status_label = Label(
            self.mode_frame, text="", font=("Arial", 8), fg=HIGHLIGHT_COLOR, bg=BG
        )
        self.status_label.pack(side=BOTTOM, pady=5)

        # Create a frame for the existing dropdown selectors
        self.selectors_frame = Frame(self.top_frame, background=BG)

        # Replace Combobox with NonBlockingDropdown for venue selection
        venue_values = [i.name for i in venues]
        self.venue_select = NonBlockingDropdown(
            self.selectors_frame,
            values=venue_values,
            current_index=[i for i in venues].index(state.venue),
            command=lambda idx: state.set_venue([i for i in venues][idx]),
            width=15,
        )
        self.venue_select.pack(side=LEFT, padx=5, pady=5)

        # Replace Combobox with NonBlockingDropdown for theme selection
        theme_values = [i.name for i in themes]
        self.theme_select = NonBlockingDropdown(
            self.selectors_frame,
            values=theme_values,
            current_index=themes.index(state.theme),
            command=lambda idx: state.set_theme(themes[idx]),
            width=15,
        )
        self.theme_select.pack(side=LEFT, padx=5, pady=5)

        # Pack the selectors frame on the right side of the top frame
        self.selectors_frame.pack(side=RIGHT, padx=10, pady=5)

        self.top_frame.pack(fill=X)

        # Create a frame for the main content with canvas and manual control
        self.main_content_frame = Frame(self, background=BG)

        # Create a frame for manual control
        self.manual_control_frame = Frame(self.main_content_frame, background=BG)

        # Add a label for the manual dimmer
        Label(
            self.manual_control_frame,
            text="Manual Dimmer",
            bg=BG,
            fg="white",
            font=("Arial", 10),
        ).pack(padx=5, pady=5)

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

        # Only show manual control if there is a manual group or manual dimmers for this venue
        if get_manual_group(self.state.venue) or has_manual_dimmer(self.state.venue):
            self.manual_control_frame.pack(side=RIGHT, fill=Y)

        # Add event handler for venue change to show/hide manual control
        self.state.events.on_venue_change += self.update_manual_control_visibility

        # Create canvas frame
        self.canvas_frame = Frame(self.main_content_frame, bg=BG)

        # Create canvas with fixed position
        self.canvas = Canvas(
            self.canvas_frame,
            width=CANVAS_WIDTH,
            height=CANVAS_HEIGHT,
            bg=BG,
            borderwidth=0,
            highlightthickness=0,
            selectborderwidth=0,
        )
        self.canvas.pack(side=LEFT, fill=BOTH, expand=True)
        self.canvas_frame.pack(side=LEFT, fill=BOTH, expand=True)

        self.main_content_frame.pack(fill=BOTH, expand=True)

        # Initialize selection and drag data
        self._drag_data = {"x": 0, "y": 0, "item": None}
        self._selection_box = {"start_x": 0, "start_y": 0, "box_id": None}
        self.selected_renderers = []  # List to track selected renderers

        # Bind mouse events
        self.canvas.bind("<ButtonPress-1>", self.drag_start)
        self.canvas.bind("<ButtonRelease-1>", self.drag_stop)
        self.canvas.bind("<B1-Motion>", self.drag)

        self.setup_patch()
        self.state.events.on_venue_change += lambda x: self.setup_patch()

        self.label_var = StringVar()
        self.label = Label(self, textvariable=self.label_var, bg=BG, fg="white")

        self.btn_frame = Frame(self, background=BG)

        # Create a left frame for most buttons
        self.left_btn_frame = Frame(self.btn_frame, background=BG)

        # Create signal buttons
        self.strobe_button = RoundedButton(
            self.left_btn_frame,
            text="Strobe",
            press_command=lambda: self._handle_signal_button_press(FrameSignal.strobe),
            release_command=lambda: self._handle_signal_button_release(
                FrameSignal.strobe
            ),
        )
        self.strobe_button.pack(side=LEFT, padx=5, pady=5)

        self.big_pulse_button = RoundedButton(
            self.left_btn_frame,
            text="Big Pulse",
            press_command=lambda: self._handle_signal_button_press(
                FrameSignal.big_pulse
            ),
            release_command=lambda: self._handle_signal_button_release(
                FrameSignal.big_pulse
            ),
        )
        self.big_pulse_button.pack(side=LEFT, padx=5, pady=5)

        self.small_pulse_button = RoundedButton(
            self.left_btn_frame,
            text="Small Pulse",
            press_command=lambda: self._handle_signal_button_press(
                FrameSignal.small_pulse
            ),
            release_command=lambda: self._handle_signal_button_release(
                FrameSignal.small_pulse
            ),
        )
        self.small_pulse_button.pack(side=LEFT, padx=5, pady=5)

        self.twinkle_button = RoundedButton(
            self.left_btn_frame,
            text="Twinkle",
            press_command=lambda: self._handle_signal_button_press(FrameSignal.twinkle),
            release_command=lambda: self._handle_signal_button_release(
                FrameSignal.twinkle
            ),
        )
        self.twinkle_button.pack(side=LEFT, padx=5, pady=5)

        self.dampen_button = RoundedButton(
            self.left_btn_frame,
            text="Dampen",
            press_command=lambda: self._handle_signal_button_press(FrameSignal.dampen),
            release_command=lambda: self._handle_signal_button_release(
                FrameSignal.dampen
            ),
        )
        self.dampen_button.pack(side=LEFT, padx=5, pady=5)

        # Pack the left frame
        self.left_btn_frame.pack(side=LEFT)

        # Create a right frame for the shift buttons and caret
        self.right_btn_frame = Frame(self.btn_frame, background=BG)

        # Add shift buttons to the right frame
        self.shift = RoundedButton(
            self.right_btn_frame, text="Shift", command=lambda: director.shift()
        )
        self.shift.pack(side=RIGHT, padx=5, pady=5)

        # Add "Shift all" button that calls generate_interpreters
        self.shift_all = RoundedButton(
            self.right_btn_frame,
            text="Shift All",
            command=lambda: director.generate_interpreters(),
        )
        self.shift_all.pack(side=RIGHT, padx=5, pady=5)

        # Add waveform toggle button with caret icon
        self.waveform_toggle_button = RoundedButton(
            self.right_btn_frame,
            text="▼",  # Down caret when visible
            command=self.toggle_waveform,
        )
        self.waveform_toggle_button.pack(side=RIGHT, padx=5, pady=5)

        # Pack the right frame
        self.right_btn_frame.pack(side=RIGHT, fill=X, expand=True)

        self.btn_frame.pack(fill=X)

        # Create waveform panel (graph)
        self.graph_frame = Frame(self, background=BG)
        if SHOW_PLOT and self.state.show_waveform:
            self.graph = Canvas(
                self.graph_frame,
                width=CANVAS_WIDTH,
                height=100,
                bg=BG,
                borderwidth=0,
                highlightthickness=0,
            )
            self.graph.pack(fill=X, expand=True)
            self.graph_frame.pack(fill=X, expand=True)
        else:
            self.graph = Canvas(
                self.graph_frame,
                width=CANVAS_WIDTH,
                height=100,
                bg=BG,
                borderwidth=0,
                highlightthickness=0,
            )
            self.graph.pack(fill=X, expand=True)
            if not self.state.show_waveform:
                self.waveform_toggle_button.config(text="▲")  # Up caret when hidden

        # Bind window resize event to adjust canvas size
        self.bind("<Configure>", self.on_window_resize)

        # Set up periodic check for GUI updates (every 100ms)
        self.after(100, self.check_gui_updates)

    def setup_patch(self):
        self.canvas.delete("all")

        # Create a flat list of fixtures and track their group membership
        self.fixtures = []
        self.fixture_group_map = {}  # Maps fixture to its group

        # Unpack all fixtures from venue_patches, flattening groups
        for item in venue_patches[self.state.venue]:
            if isinstance(item, FixtureGroup):
                # Add all fixtures from the group to our flat list
                for fixture in item.fixtures:
                    self.fixtures.append(fixture)
                    self.fixture_group_map[fixture] = item
            else:
                # Individual fixture
                self.fixtures.append(item)
                self.fixture_group_map[item] = None  # No group

        # Create renderers for all fixtures in our flat list
        self.fixture_renderers = [
            renderer_for_fixture(fixture) for fixture in self.fixtures
        ]

        # Set up all renderers
        for renderer in self.fixture_renderers:
            renderer.setup(self.canvas)

        # Group renderers by their fixture group
        grouped_renderers = {}
        for renderer in self.fixture_renderers:
            group = self.fixture_group_map.get(renderer.fixture)
            group_id = id(group) if group else None
            if group_id not in grouped_renderers:
                grouped_renderers[group_id] = []
            grouped_renderers[group_id].append(renderer)

        # Position renderers, with each group on its own row
        fixture_y = FIXTURE_MARGIN
        max_y = 0

        # Process each group
        for group_id, renderers in grouped_renderers.items():
            # Calculate the total width of all renderers in this group
            total_width = sum(
                renderer.width for renderer in renderers
            ) + FIXTURE_MARGIN * (len(renderers) - 1)

            # Determine how many fixtures can fit in a row
            max_fixtures_per_row = max(
                1,
                (CANVAS_WIDTH - 2 * FIXTURE_MARGIN)
                // (renderers[0].width + FIXTURE_MARGIN),
            )

            # Split renderers into rows
            rows = []
            current_row = []
            current_row_width = 0

            for renderer in renderers:
                # If adding this renderer would exceed the canvas width or max fixtures per row, start a new row
                if (
                    len(current_row) >= max_fixtures_per_row
                    or current_row_width + renderer.width + FIXTURE_MARGIN
                    > CANVAS_WIDTH - FIXTURE_MARGIN
                ):
                    rows.append(current_row)
                    current_row = []
                    current_row_width = 0

                current_row.append(renderer)
                current_row_width += renderer.width + FIXTURE_MARGIN

            # Add the last row if it's not empty
            if current_row:
                rows.append(current_row)

            # Position renderers in each row
            for row in rows:
                # Calculate the starting x position to center the row
                row_width = sum(renderer.width for renderer in row) + FIXTURE_MARGIN * (
                    len(row) - 1
                )
                fixture_x = max(FIXTURE_MARGIN, (CANVAS_WIDTH - row_width) // 2)

                # Position each renderer in the row
                for renderer in row:
                    renderer.set_position(self.canvas, fixture_x, fixture_y)
                    fixture_x += renderer.width + FIXTURE_MARGIN

                # Move to the next row
                max_row_height = max(renderer.height for renderer in row)
                fixture_y += max_row_height + FIXTURE_MARGIN
                max_y = max(max_y, fixture_y)

            # Add extra spacing between groups
            fixture_y += FIXTURE_MARGIN * 2

        # Load fixture positions from saved file
        self.load()

        # Clear selected renderers when changing venue
        self.selected_renderers = []

    def _force_update_button_appearance(self, mode):
        """Force update the button appearance for the given mode."""
        if not mode or mode.name not in self.mode_buttons:
            return

        print(f"GUI: Force updating button appearance for {mode.name}")

        # First reset ALL buttons to default appearance
        for btn_name, btn in self.mode_buttons.items():
            if btn_name != mode.name:  # Skip the button we're about to highlight
                btn.config(
                    background=BG,
                    foreground=BUTTON_FG,
                    highlightthickness=0,
                    highlightbackground=BG,
                    borderwidth=1,
                    relief=FLAT,
                )
                btn.update_idletasks()

        # Get the button
        button = self.mode_buttons[mode.name]

        # Apply highlighting
        button.config(
            background=BG,
            foreground=HIGHLIGHT_COLOR,
            highlightthickness=2,
            highlightbackground=HIGHLIGHT_COLOR,
            borderwidth=1,
            relief=FLAT,
        )

        # Force update
        button.update_idletasks()

        # Update the root window to ensure changes are visible
        self.update_idletasks()

    def _select_mode(self, mode):
        """Handle mode button selection and update UI."""
        # Do nothing if the mode is already selected
        if self.state.mode == mode:
            return

        # Set flag to indicate this is a local change
        self.local_mode_change = True

        # Update the state
        self.state.set_mode(mode)

        # Generate new interpreters for the selected mode
        self.director.generate_interpreters()

        # Update button appearances
        self._update_mode_buttons(mode)

        # Force update the button appearance
        self._force_update_button_appearance(mode)

        # Reset the flag
        self.local_mode_change = False

    def on_mode_change(self, mode):
        """Update the mode selection when the state changes."""
        if mode:
            print(f"GUI: on_mode_change called for {mode.name}")

            # Generate new interpreters for the changed mode
            self.director.generate_interpreters()

            # Update the mode variable to match the current mode
            if hasattr(self, "mode_var"):
                self.mode_var.set(mode.name)

            # Only show web app notification if this wasn't a local change
            if not self.local_mode_change and mode.name in self.mode_buttons:
                print(f"GUI: External change detected for mode {mode.name}")

                # Schedule multiple updates to ensure the UI refreshes
                # This is a workaround for Tkinter's sometimes unreliable updates
                def update_ui():
                    print(f"GUI: Scheduled update for {mode.name}")
                    # Update all buttons first
                    self._update_mode_buttons(mode)
                    # Force update the button appearance
                    self._force_update_button_appearance(mode)
                    # Flash the button
                    button = self.mode_buttons[mode.name]
                    button.config(background=HIGHLIGHT_COLOR, foreground=BG)
                    button.update_idletasks()
                    # Show status message
                    self.status_label.config(
                        text=f"mode changed to '{mode.name}' from web app"
                    )
                    # Schedule reset
                    self.after(300, lambda: reset_button())

                def reset_button():
                    print(f"GUI: Resetting button for {mode.name}")
                    button = self.mode_buttons[mode.name]
                    if button.winfo_exists():
                        # Update all buttons again
                        self._update_mode_buttons(mode)
                        # Force update again
                        self._force_update_button_appearance(mode)
                    # Clear status after a delay
                    self.after(4700, lambda: self.status_label.config(text=""))

                # Schedule the update to run after a short delay
                # This gives time for the GUI to become responsive
                self.after_idle(update_ui)
                # Also schedule a backup update in case the first one doesn't work
                self.after(200, update_ui)
            else:
                # Always update button appearances, even for local changes
                print(f"GUI: Updating buttons for local change to {mode.name}")
                self._update_mode_buttons(mode)
                # Force update the button appearance
                self._force_update_button_appearance(mode)

    def _update_mode_buttons(self, mode):
        """Update the appearance of mode buttons based on selection."""
        if not mode:
            print("GUI: Cannot update buttons - mode is None")
            return

        print(f"GUI: Updating all mode buttons, highlighting {mode.name}")

        # Update all buttons
        for btn_name, btn in self.mode_buttons.items():
            if btn_name == mode.name:
                # Selected button style
                btn.config(
                    background=BG,
                    foreground=HIGHLIGHT_COLOR,
                    highlightthickness=2,
                    highlightbackground=HIGHLIGHT_COLOR,
                    borderwidth=1,
                    relief=FLAT,
                )
            else:
                # Non-selected button style
                btn.config(
                    background=BG,
                    foreground=BUTTON_FG,
                    highlightthickness=0,
                    highlightbackground=BG,
                    borderwidth=1,
                    relief=FLAT,
                )
            btn.update_idletasks()

        # Force update the window
        self.update_idletasks()

    def select_renderer(self, renderer, add_to_selection=False):
        """Select a renderer and show a white outline."""
        if not add_to_selection:
            # Deselect all currently selected renderers
            self.deselect_all_renderers()

        # Add to selection if not already selected
        if renderer not in self.selected_renderers:
            self.selected_renderers.append(renderer)

            # Add white outline to the fixture shape(s)
            # Handle BulbRenderer and variants
            if hasattr(renderer, "oval"):
                self.canvas.itemconfig(
                    renderer.oval,
                    outline=SELECTION_OUTLINE_COLOR,
                    width=SELECTION_OUTLINE_WIDTH,
                )

            # Handle RoundedRectBulbRenderer
            if hasattr(renderer, "rect_v"):
                self.canvas.itemconfig(
                    renderer.rect_v,
                    outline=SELECTION_OUTLINE_COLOR,
                    width=SELECTION_OUTLINE_WIDTH,
                )

            if hasattr(renderer, "corners"):
                for corner in renderer.corners:
                    self.canvas.itemconfig(
                        corner,
                        outline=SELECTION_OUTLINE_COLOR,
                        width=SELECTION_OUTLINE_WIDTH,
                    )

            # Handle MovingHeadRenderer
            if hasattr(renderer, "base"):
                self.canvas.itemconfig(
                    renderer.base,
                    outline=SELECTION_OUTLINE_COLOR,
                    width=SELECTION_OUTLINE_WIDTH,
                )
                self.canvas.itemconfig(
                    renderer.head,
                    outline=SELECTION_OUTLINE_COLOR,
                    width=SELECTION_OUTLINE_WIDTH,
                )
                self.canvas.itemconfig(
                    renderer.light,
                    outline=SELECTION_OUTLINE_COLOR,
                    width=SELECTION_OUTLINE_WIDTH,
                )

            # Handle MotionstripRenderer and ColorBandRenderer
            if hasattr(renderer, "shape"):
                self.canvas.itemconfig(
                    renderer.shape,
                    outline=SELECTION_OUTLINE_COLOR,
                    width=SELECTION_OUTLINE_WIDTH,
                )
                if hasattr(renderer, "bulbs"):
                    for bulb in renderer.bulbs:
                        self.canvas.itemconfig(
                            bulb,
                            outline=SELECTION_OUTLINE_COLOR,
                            width=SELECTION_OUTLINE_WIDTH,
                        )

            # Make the patch label white
            if renderer.patch_label:
                self.canvas.itemconfig(
                    renderer.patch_label, fill=SELECTION_OUTLINE_COLOR
                )

    def deselect_renderer(self, renderer):
        """Deselect a renderer and remove white outline."""
        if renderer in self.selected_renderers:
            self.selected_renderers.remove(renderer)

            # Remove white outline from the fixture shape(s)
            # Handle BulbRenderer and variants
            if hasattr(renderer, "oval"):
                self.canvas.itemconfig(
                    renderer.oval,
                    outline=DEFAULT_OUTLINE_COLOR,
                    width=DEFAULT_OUTLINE_WIDTH,
                )

            # Handle RoundedRectBulbRenderer
            if hasattr(renderer, "rect_v"):
                self.canvas.itemconfig(
                    renderer.rect_v,
                    outline=DEFAULT_OUTLINE_COLOR,
                    width=DEFAULT_OUTLINE_WIDTH,
                )

            if hasattr(renderer, "corners"):
                for corner in renderer.corners:
                    self.canvas.itemconfig(
                        corner,
                        outline=DEFAULT_OUTLINE_COLOR,
                        width=DEFAULT_OUTLINE_WIDTH,
                    )

            # Handle MovingHeadRenderer
            if hasattr(renderer, "base"):
                self.canvas.itemconfig(
                    renderer.base,
                    outline=DEFAULT_OUTLINE_COLOR,
                    width=DEFAULT_OUTLINE_WIDTH,
                )
                self.canvas.itemconfig(
                    renderer.head,
                    outline=DEFAULT_OUTLINE_COLOR,
                    width=DEFAULT_OUTLINE_WIDTH,
                )
                self.canvas.itemconfig(
                    renderer.light,
                    outline=DEFAULT_OUTLINE_COLOR,
                    width=DEFAULT_OUTLINE_WIDTH,
                )

            # Handle MotionstripRenderer and ColorBandRenderer
            if hasattr(renderer, "shape"):
                self.canvas.itemconfig(
                    renderer.shape,
                    outline=DEFAULT_OUTLINE_COLOR,
                    width=DEFAULT_OUTLINE_WIDTH,
                )
                if hasattr(renderer, "bulbs"):
                    for bulb in renderer.bulbs:
                        self.canvas.itemconfig(
                            bulb,
                            outline=DEFAULT_OUTLINE_COLOR,
                            width=DEFAULT_OUTLINE_WIDTH,
                        )

            # Make the patch label gray again
            if renderer.patch_label:
                self.canvas.itemconfig(renderer.patch_label, fill="gray")

    def deselect_all_renderers(self):
        """Deselect all renderers."""
        # Create a copy of the list to avoid modification during iteration
        renderers_to_deselect = self.selected_renderers.copy()
        for renderer in renderers_to_deselect:
            self.deselect_renderer(renderer)

        # Ensure the list is empty
        self.selected_renderers = []

    def drag_start(self, event):
        """Beginning drag of an object or selection box"""
        # Get canvas coordinates
        canvas_x = event.x
        canvas_y = event.y

        # Find if we clicked on a fixture
        clicked_renderer = None
        closest = 999999999

        for renderer in self.fixture_renderers:
            if renderer.contains_point(canvas_x, canvas_y):
                dist = distance(
                    (canvas_x, canvas_y),
                    (renderer.x + renderer.width / 2, renderer.y + renderer.height / 2),
                )
                if dist < closest:
                    closest = dist
                    clicked_renderer = renderer

        if clicked_renderer is not None:
            # Check if we clicked on an already selected renderer
            if clicked_renderer in self.selected_renderers:
                # Just set the drag item (all selected renderers will move)
                self._drag_data["item"] = clicked_renderer
            else:
                # Select this renderer (deselecting others unless Shift is held)
                add_to_selection = event.state & 0x0001  # Check if Shift key is pressed
                self.select_renderer(clicked_renderer, add_to_selection)
                self._drag_data["item"] = clicked_renderer
        else:
            # Start drawing a selection box
            self._selection_box["start_x"] = canvas_x
            self._selection_box["start_y"] = canvas_y

            # Create the selection box with just an outline (no fill)
            self._selection_box["box_id"] = self.canvas.create_rectangle(
                canvas_x,
                canvas_y,
                canvas_x,
                canvas_y,
                outline=SELECTION_BOX_COLOR,
                fill="",  # No fill, just an outline
                width=1,
            )

            # Deselect all renderers when starting a new selection box
            self.deselect_all_renderers()

        # Record the current mouse position for drag calculations
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def drag_stop(self, event):
        """End drag of an object or selection box"""
        # If we were drawing a selection box
        if self._selection_box["box_id"] is not None:
            # Get the final box coordinates
            canvas_x = event.x
            canvas_y = event.y

            # Get the box coordinates
            x1 = min(self._selection_box["start_x"], canvas_x)
            y1 = min(self._selection_box["start_y"], canvas_y)
            x2 = max(self._selection_box["start_x"], canvas_x)
            y2 = max(self._selection_box["start_y"], canvas_y)

            # Select all renderers inside the box
            for renderer in self.fixture_renderers:
                # Check if the renderer is inside the selection box
                if (
                    renderer.x < x2
                    and renderer.x + renderer.width > x1
                    and renderer.y < y2
                    and renderer.y + renderer.height > y1
                ):
                    self.select_renderer(renderer, add_to_selection=True)

            # Delete the selection box
            self.canvas.delete(self._selection_box["box_id"])
            self._selection_box["box_id"] = None

        # If we were dragging fixtures, save their positions
        if self._drag_data["item"] is not None:
            self.save()

        # Reset the drag information
        self._drag_data["item"] = None
        self._drag_data["x"] = 0
        self._drag_data["y"] = 0

    def drag(self, event):
        """Handle dragging of objects or selection box"""
        # If we're drawing a selection box
        if self._selection_box["box_id"] is not None:
            # Update the selection box size
            canvas_x = event.x
            canvas_y = event.y

            self.canvas.coords(
                self._selection_box["box_id"],
                self._selection_box["start_x"],
                self._selection_box["start_y"],
                canvas_x,
                canvas_y,
            )
            return

        # If we're dragging fixtures
        if self._drag_data["item"] is None:
            return

        # Compute how much the mouse has moved
        delta_x = event.x - self._drag_data["x"]
        delta_y = event.y - self._drag_data["y"]

        # Always use CANVAS_WIDTH for consistent positioning
        canvas_width = CANVAS_WIDTH
        canvas_height = CANVAS_HEIGHT

        # If we have selected renderers, move all of them
        if self.selected_renderers:
            for renderer in self.selected_renderers:
                # Calculate the new position
                new_x = renderer.x + delta_x
                new_y = renderer.y + delta_y

                # Clamp the position within the canvas boundaries
                min_x = FIXTURE_MARGIN
                max_x = canvas_width - renderer.width - FIXTURE_MARGIN
                new_x = max(min_x, min(new_x, max_x))

                # Clamp y position as well for fixed canvas
                min_y = FIXTURE_MARGIN
                max_y = canvas_height - renderer.height - FIXTURE_MARGIN
                new_y = max(min_y, min(new_y, max_y))

                # Move the renderer
                renderer.set_position(self.canvas, new_x, new_y)

        # Record the new position
        self._drag_data["x"] = event.x
        self._drag_data["y"] = event.y

    def step(self, frame: parrot.director.frame.Frame):
        # Process any pending GUI updates from the web app
        self.state.process_gui_updates()

        # Update the frame with our signal states
        frame.extend(self.signal_states.get_states())

        # Continue with normal rendering
        for renderer in self.fixture_renderers:
            renderer.render(self.canvas, frame)

        if SHOW_PLOT and self.state.show_waveform:
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

        # Save all renderers from our flat list
        for renderer in self.fixture_renderers:
            # Create position data directly from current coordinates
            position_data = {"x": renderer.x, "y": renderer.y}

            # Clamp the position within the canvas boundaries
            position_data = self._clamp_position(position_data, renderer)

            data[renderer.fixture.id] = position_data

        # write to file
        with open(filename, "w") as f:
            json.dump(data, f, indent=4)

    def load(self):
        filename = f"{self.state.venue.name}_gui.json"

        # Check if the file exists
        if not os.path.exists(filename):
            print(f"No saved layout found for {self.state.venue.name}")
            return

        # Load the data from the file
        try:
            with open(filename, "r") as f:
                data = json.load(f)
        except Exception as e:
            print(f"Error loading layout: {e}")
            return

        # Track if we found any new fixtures that weren't in the saved data
        new_fixtures_added = False

        # Load position data for all renderers in our flat list
        for renderer in self.fixture_renderers:
            if renderer.fixture.id in data:
                # Get the position data
                position_data = data[renderer.fixture.id]

                # Clamp the position within the canvas boundaries
                position_data = self._clamp_position(position_data, renderer)

                # Directly set the position instead of using from_json to ensure proper positioning
                renderer.set_position(
                    self.canvas, position_data["x"], position_data["y"]
                )
            else:
                # This is a new fixture that wasn't in the saved data
                new_fixtures_added = True

        # If new fixtures were added, save the updated configuration
        if new_fixtures_added:
            self.save()

    def _clamp_position(self, position_data, renderer):
        """Clamp the position within the canvas boundaries.
        For a fixed canvas, we need to clamp both x and y coordinates.
        """
        # Create a copy of the position data to avoid modifying the original
        clamped_data = position_data.copy()

        # Always use CANVAS_WIDTH for consistent positioning
        # This ensures positions are consistent between saves and loads
        canvas_width = CANVAS_WIDTH
        canvas_height = CANVAS_HEIGHT

        # Clamp x position to keep fixtures within the horizontal bounds
        min_x = FIXTURE_MARGIN
        max_x = canvas_width - renderer.width - FIXTURE_MARGIN

        # Only apply clamping if the position is significantly outside the bounds
        # This prevents minor adjustments that could disrupt existing layouts
        if clamped_data["x"] < 0 or clamped_data["x"] > canvas_width:
            clamped_data["x"] = max(min_x, min(clamped_data["x"], max_x))

        # Clamp y position to keep fixtures within the vertical bounds
        min_y = FIXTURE_MARGIN
        max_y = canvas_height - renderer.height - FIXTURE_MARGIN

        # Apply y clamping if the position is outside the bounds
        if clamped_data["y"] < 0 or clamped_data["y"] > canvas_height:
            clamped_data["y"] = max(min_y, min(clamped_data["y"], max_y))

        return clamped_data

    def update_manual_control_visibility(self, venue):
        """Show or hide manual control based on whether there is a manual group or manual dimmers for this venue."""
        if get_manual_group(venue) or has_manual_dimmer(venue):
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

            # Find all renderers for fixtures in the manual group and update them
            empty_frame = DirectorFrame({})  # Create an empty frame with default values

            for renderer in self.fixture_renderers:
                if (
                    hasattr(renderer.fixture, "parent_group")
                    and renderer.fixture.parent_group == manual_group
                ):
                    # Force a render update for the manual fixture
                    renderer.render(self.canvas, empty_frame)

        # Even if there's no manual group, we still want to update the state
        # This allows venues with manual dimmers but no manual group to use the slider value

    def toggle_waveform(self):
        """Toggle the waveform panel visibility."""
        new_state = not self.state.show_waveform
        self.state.set_show_waveform(new_state)

        if new_state:
            # Show waveform
            self.waveform_toggle_button.config(text="▼")  # Down caret
            self.graph_frame.pack(fill=X, expand=True)
        else:
            # Hide waveform
            self.waveform_toggle_button.config(text="▲")  # Up caret
            self.graph_frame.pack_forget()

        # Adjust canvas size after showing/hiding waveform
        self.on_window_resize(None)

    def on_window_resize(self, event):
        """Adjust canvas size when window is resized."""
        # If called directly (not from event), create a dummy event
        if event is None:

            class DummyEvent:
                pass

            event = DummyEvent()
            event.widget = self
            event.height = self.winfo_height()

        # Only respond to the main window's resize events
        if event.widget == self:
            # Calculate available height for canvas
            # (window height minus space needed for other widgets)
            other_widgets_height = (
                self.top_frame.winfo_height() + self.btn_frame.winfo_height()
            )
            if hasattr(self, "graph_frame") and self.state.show_waveform:
                other_widgets_height += self.graph_frame.winfo_height()

            # Add some padding
            other_widgets_height += 40

            # Calculate new canvas height
            new_height = max(400, event.height - other_widgets_height)

            # Update canvas height
            self.canvas.config(height=new_height)

    def check_gui_updates(self):
        """Periodically check for GUI updates from other threads (like the web app)."""
        # Process any pending updates
        try:
            self.state.process_gui_updates()

            # Force a refresh of the UI
            self.update_idletasks()

            # Check if any mode buttons need to be refreshed
            if self.state.mode and self.state.mode.name in self.mode_buttons:
                # Count how many buttons are highlighted
                highlighted_buttons = 0
                for btn_name, btn in self.mode_buttons.items():
                    if btn.cget("highlightbackground") == HIGHLIGHT_COLOR:
                        highlighted_buttons += 1
                        if btn_name != self.state.mode.name:
                            # Found a button that shouldn't be highlighted
                            print(
                                f"GUI: Found incorrect highlight on {btn_name}, fixing..."
                            )
                            btn.config(
                                background=BG,
                                foreground=BUTTON_FG,
                                highlightthickness=0,
                                highlightbackground=BG,
                                borderwidth=1,
                                relief=FLAT,
                            )
                            btn.update_idletasks()

                # Ensure the current mode button is properly highlighted
                current_button = self.mode_buttons[self.state.mode.name]
                if (
                    current_button.cget("highlightbackground") != HIGHLIGHT_COLOR
                    or highlighted_buttons != 1
                ):
                    print(
                        f"GUI: Fixing highlight for {self.state.mode.name} in periodic check"
                    )
                    self._force_update_button_appearance(self.state.mode)
        except Exception as e:
            print(f"Error in GUI update check: {e}")

        # Schedule the next check (every 100ms for more responsive updates)
        self.after(100, self.check_gui_updates)

    def _handle_signal_button_release(self, signal: FrameSignal):
        """Handle signal button release."""
        # Get the button
        button = getattr(self, f"{signal.name}_button")

        # Set signal to low
        self.signal_states.set_signal(signal, 0.0)

        button.config(
            background=BUTTON_BG,
            foreground=BUTTON_FG,
        )

    def _handle_signal_button_press(self, signal: FrameSignal):
        """Handle signal button press/release."""
        # Get the button
        button = getattr(self, f"{signal.name}_button")

        # Press the button
        button.config(
            background=BUTTON_ACTIVE_BG,
            foreground=BUTTON_ACTIVE_FG,
        )
        # Set signal to high
        self.signal_states.set_signal(signal, 1.0)

        # Update the button state
        button.update_idletasks()
