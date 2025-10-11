import json
import os
import queue
from events import Events
from beartype import beartype
from parrot.director.mode import Mode
from parrot.vj.vj_mode import VJMode
from parrot.director.themes import themes, get_theme_by_name
from parrot.patch_bay import venues


@beartype
class State:
    def __init__(self):
        self.events = Events()

        # Default values
        self._mode = Mode.chill  # Default mode
        self._vj_mode = VJMode.full_rave  # Default VJ mode
        self._hype = 30
        self._theme = themes[0]
        self._venue = venues.dmack
        self._manual_dimmer = 0  # New property for manual control
        self._hype_limiter = False  # Start with hype limiter OFF
        self._show_waveform = True  # New property for waveform visibility
        self._show_fixture_mode = False  # Default to VJ mode, not fixture mode

        # Queue for GUI updates from other threads
        self._gui_update_queue = queue.Queue()

        # Initialize signal states
        from parrot.director.signal_states import SignalStates

        self.signal_states = SignalStates()

        # Try to load state from file
        self.load_state()

    @property
    def mode(self):
        return self._mode

    def set_mode(self, value: Mode):
        if self._mode == value:
            return

        self._mode = value
        self.events.on_mode_change(self._mode)
        self.save_state()

    def set_mode_thread_safe(self, value: Mode):
        """Set the mode (now safe since web server runs on main thread)."""
        # Since web server now runs on main thread, just call the regular method
        self.set_mode(value)
        print(f"Mode changed from web interface to: {value.name}")

    def set_effect_thread_safe(self, effect: str):
        """Set the effect in a thread-safe way."""
        try:
            from parrot.director.frame import FrameSignal

            signal = FrameSignal[effect]
            if hasattr(self, "signal_states"):
                self.signal_states.set_signal(signal, 1.0)
                print(f"Thread-safe effect change to: {effect}")
        except Exception as e:
            print(f"Error setting effect: {e}")
            raise

    @property
    def vj_mode(self):
        return self._vj_mode

    def set_vj_mode(self, value: VJMode):
        if self._vj_mode == value:
            return

        self._vj_mode = value
        self.events.on_vj_mode_change(self._vj_mode)
        self.save_state()

    def set_vj_mode_thread_safe(self, value: VJMode):
        """Set the VJ mode (now safe since web server runs on main thread)."""
        # Since web server now runs on main thread, just call the regular method
        self.set_vj_mode(value)
        print(f"VJ mode changed from web interface to: {value.name}")

    @property
    def hype(self):
        return self._hype

    def set_hype(self, value: float):
        if self._hype == value:
            return

        self._hype = value
        self.events.on_hype_change(self._hype)

    @property
    def theme(self):
        return self._theme

    def set_theme(self, value):
        if self._theme == value:
            return

        self._theme = value
        self.events.on_theme_change(self._theme)
        self.save_state()

    @property
    def venue(self):
        return self._venue

    def set_venue(self, value):
        if self._venue == value:
            return

        self._venue = value
        self.events.on_venue_change(self._venue)
        self.save_state()

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

    @property
    def show_waveform(self):
        return self._show_waveform

    def set_show_waveform(self, value):
        if self._show_waveform == value:
            return

        self._show_waveform = value
        self.events.on_show_waveform_change(self._show_waveform)

    @property
    def show_fixture_mode(self):
        return self._show_fixture_mode

    def set_show_fixture_mode(self, value):
        if self._show_fixture_mode == value:
            return

        self._show_fixture_mode = value
        self.events.on_show_fixture_mode_change(self._show_fixture_mode)
        self.save_state()

    def save_state(self):
        """Save the current state to a JSON file."""
        state_data = {
            "mode": self._mode.name if self._mode else None,
            "hype": self._hype,
            "theme_name": self._theme.name if hasattr(self._theme, "name") else None,
            "venue_name": self._venue.name if hasattr(self._venue, "name") else None,
            "manual_dimmer": 0,  # We do not want to restart the app with lights on
            "hype_limiter": self._hype_limiter,
            "show_waveform": self._show_waveform,
            "show_fixture_mode": self._show_fixture_mode,
            "vj_mode": self._vj_mode.name if self._vj_mode else None,
        }

        try:
            with open("state.json", "w") as f:
                json.dump(state_data, f, indent=2)
        except Exception as e:
            print(f"Error saving state: {e}")

    def load_state(self):
        """Load state from a JSON file if it exists."""
        if not os.path.exists("state.json"):
            return

        try:
            with open("state.json", "r") as f:
                state_data = json.load(f)

            # Set values from loaded state
            if "mode" in state_data and state_data["mode"]:
                try:
                    self._mode = Mode[state_data["mode"]]
                except KeyError:
                    print(f"Mode '{state_data['mode']}' not found, using default")

            if "hype" in state_data:
                self._hype = state_data["hype"]

            # Handle theme loading - try theme_name first, then fall back to theme_index for backward compatibility
            if "theme_name" in state_data and state_data["theme_name"]:
                try:
                    self._theme = get_theme_by_name(state_data["theme_name"])
                except ValueError:
                    # If theme name not found, keep default
                    print(
                        f"Theme '{state_data['theme_name']}' not found, using default"
                    )
            elif "theme_index" in state_data and 0 <= state_data["theme_index"] < len(
                themes
            ):
                # Backward compatibility with old format
                self._theme = themes[state_data["theme_index"]]

            if "venue_name" in state_data and state_data["venue_name"]:
                # Find venue by name
                for venue in venues.__dict__.values():
                    if (
                        hasattr(venue, "name")
                        and venue.name == state_data["venue_name"]
                    ):
                        self._venue = venue
                        break

            if "manual_dimmer" in state_data:
                self._manual_dimmer = state_data["manual_dimmer"]

            if "hype_limiter" in state_data:
                self._hype_limiter = state_data["hype_limiter"]

            if "show_waveform" in state_data:
                self._show_waveform = state_data["show_waveform"]

            if "show_fixture_mode" in state_data:
                self._show_fixture_mode = state_data["show_fixture_mode"]

            if "vj_mode" in state_data and state_data["vj_mode"]:
                try:
                    self._vj_mode = VJMode[state_data["vj_mode"]]
                except KeyError:
                    print(f"VJ mode '{state_data['vj_mode']}' not found, using default")

        except Exception as e:
            print(f"Error loading state: {e}")

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

                elif update_type == "vj_mode":
                    # Update the VJ mode on the main thread
                    if self._vj_mode != value:
                        self._vj_mode = value
                        # Trigger all event handlers (OpenGL operations are safe on main thread)
                        if hasattr(self.events, "on_vj_mode_change"):
                            handlers = getattr(self.events, "on_vj_mode_change")
                            for handler in list(handlers):
                                try:
                                    handler(value)
                                except Exception as e:
                                    print(f"Error in VJ mode event handler: {e}")

                # Mark the task as done
                self._gui_update_queue.task_done()

        except queue.Empty:
            # No more updates to process
            pass
