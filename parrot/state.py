import json
import os
from events import Events
from parrot.director.phrase import Phrase
from parrot.director.themes import themes, get_theme_by_name
from parrot.patch_bay import venues


class State:
    def __init__(self):
        self.events = Events()

        # Default values
        self._phrase = None
        self._hype = 30
        self._theme = themes[0]
        self._venue = venues.dmack
        self._manual_dimmer = 0  # New property for manual control
        self._hype_limiter = True  # New property for hype limiter

        # Try to load state from file
        self.load_state()

    @property
    def phrase(self):
        return self._phrase

    def set_phrase(self, value: Phrase):
        if self._phrase == value:
            return

        self._phrase = value
        self.events.on_phrase_change(self._phrase)

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

    @property
    def venue(self):
        return self._venue

    def set_venue(self, value):
        if self._venue == value:
            return

        self._venue = value
        self.events.on_venue_change(self._venue)

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

    def save_state(self):
        """Save the current state to a JSON file."""
        state_data = {
            "hype": self._hype,
            "theme_name": self._theme.name if hasattr(self._theme, "name") else None,
            "venue_name": self._venue.name if hasattr(self._venue, "name") else None,
            "manual_dimmer": self._manual_dimmer,
            "hype_limiter": self._hype_limiter,
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

        except Exception as e:
            print(f"Error loading state: {e}")
