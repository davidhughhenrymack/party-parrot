import json
import os
import queue
from events import Events
from parrot.director.mode import Mode
from parrot.director.themes import themes, get_theme_by_name, Theme
from parrot.patch_bay import venues
from typing import Dict


class State:
    def __init__(self):
        self.events = Events()

        # Default values
        self._mode = Mode.party
        self._hype = 0
        self._theme = get_theme_by_name("Rave")
        self._venue = venues.truckee_theatre
        self._manual_dimmer = 0  # New property for manual control
        self._hype_limiter = False  # Start with hype limiter OFF
        self._show_waveform = True  # New property for waveform visibility
        self.scene_values = {}  # Track scene slider values

        # Queue for GUI updates from other threads
        self._gui_update_queue = queue.Queue()

        # Try to load state from file
        self.load()

    @property
    def mode(self):
        return self._mode

    def set_mode(self, value: Mode):
        if self._mode == value:
            return

        self._mode = value
        self.events.on_mode_change(self._mode)
        self.save()

    def set_mode_thread_safe(self, value: Mode):
        """Set the mode in a thread-safe way, avoiding GUI updates."""
        if self._mode == value:
            return

        self._mode = value
        print(f"Thread-safe mode change to: {value.name}")

        # Manually trigger only non-GUI event handlers
        if hasattr(self.events, "on_mode_change"):
            handlers = getattr(self.events, "on_mode_change")
            # Filter out GUI-related handlers
            for handler in list(handlers):
                if "gui" not in handler.__module__:
                    try:
                        handler(value)
                    except Exception as e:
                        print(f"Error in event handler: {e}")

        # Queue the update for the GUI to process in the main thread
        self._gui_update_queue.put(("mode", value))
        print(f"Queued GUI update for mode: {value.name}")

        # Also try to directly update the GUI if possible
        # This is a workaround for cases where the queue isn't being processed
        try:
            import tkinter as tk

            for handler in list(handlers):
                if "gui" in handler.__module__:
                    # Schedule the handler to run in the main thread after a short delay
                    # This gives time for the GUI to become responsive
                    for window in tk.Tk.winfo_children(tk._default_root):
                        if hasattr(window, "after"):
                            print(
                                f"Scheduling direct GUI update for mode: {value.name}"
                            )
                            window.after(100, lambda v=value, h=handler: h(v))
                            break
        except Exception as e:
            print(f"Could not schedule direct GUI update: {e}")
            # Fall back to queue-based updates

    @property
    def hype(self):
        return self._hype

    def set_hype(self, value: float):
        if self._hype == value:
            return

        self._hype = value
        self.events.on_hype_change(self._hype)
        self.save()

    @property
    def theme(self):
        return self._theme

    def set_theme(self, value):
        if self._theme == value:
            return

        self._theme = value
        self.events.on_theme_change(self._theme)
        self.save()

    @property
    def venue(self):
        return self._venue

    def set_venue(self, value):
        if self._venue == value:
            return

        self._venue = value
        self.events.on_venue_change(self._venue)
        self.save()

    @property
    def manual_dimmer(self):
        return self._manual_dimmer

    def set_manual_dimmer(self, value):
        if self._manual_dimmer == value:
            return

        self._manual_dimmer = value
        self.events.on_manual_dimmer_change(self._manual_dimmer)

    @property
    def hype_limiter(self):
        return self._hype_limiter

    def set_hype_limiter(self, value):
        if self._hype_limiter == value:
            return

        self._hype_limiter = value
        self.events.on_hype_limiter_change(self._hype_limiter)
        self.save()

    @property
    def show_waveform(self):
        return self._show_waveform

    def set_show_waveform(self, value):
        if self._show_waveform == value:
            return

        self._show_waveform = value
        self.events.on_show_waveform_change(self._show_waveform)
        self.save()

    def set_scene_value(self, scene_name: str, value: float):
        """Set the value for a scene (0-1)."""
        self.scene_values[scene_name] = value
        self.save()

    def save(self):
        """Save state to file."""
        data = {
            "hype": self._hype,
            "theme_name": self._theme.name,
            "venue_name": self._venue.name,
            "mode": self._mode.name,
            "hype_limiter": self._hype_limiter,
            "show_waveform": self._show_waveform,
            "scene_values": self.scene_values,
        }
        with open("state.json", "w") as f:
            json.dump(data, f)

    def load(self):
        """Load state from file."""
        if os.path.exists("state.json"):
            with open("state.json", "r") as f:
                data = json.load(f)
                self._hype = data.get("hype", 0)
                self._theme = get_theme_by_name(data.get("theme_name", "Rave"))
                self._venue = getattr(venues, data.get("venue_name", "truckee_theatre"))
                self._mode = getattr(Mode, data.get("mode", "party"))
                self._hype_limiter = data.get("hype_limiter", False)
                self._show_waveform = data.get("show_waveform", True)
                self.scene_values = data.get("scene_values", {})

    def process_gui_updates(self):
        """Process any pending GUI updates from the queue."""
        try:
            while True:
                # Get update from queue (non-blocking)
                update = self._gui_update_queue.get_nowait()

                # Process the update
                update_type, value = update

                if update_type == "mode":
                    # Update the mode in the GUI
                    if self._mode != value:
                        self._mode = value
                        # Only trigger GUI-related handlers
                        if hasattr(self.events, "on_mode_change"):
                            handlers = getattr(self.events, "on_mode_change")
                            for handler in list(handlers):
                                if "gui" in handler.__module__:
                                    try:
                                        handler(value)
                                    except Exception as e:
                                        print(f"Error in GUI event handler: {e}")

                # Mark the task as done
                self._gui_update_queue.task_done()

        except queue.Empty:
            # No more updates to process
            pass


# Create a singleton instance
state_instance = State()
