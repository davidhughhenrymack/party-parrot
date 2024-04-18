from events import Events
from parrot.director.phrase import Phrase
from parrot.director.themes import themes
from parrot.patch_bay import venues


class State:
    def __init__(self):
        self.events = Events()

        self._phrase = None
        self._hype = 75
        self._theme = themes[0]
        self._venue = venues.mtn_lotus

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
