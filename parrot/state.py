from events import Events
from parrot.interpreters.base import Phrase


class State:
    def __init__(self):
        self.events = Events()
        self._phrase = None

    @property
    def phrase(self):
        return self._phrase

    def set_phrase(self, value: Phrase):
        if self._phrase == value:
            return

        self._phrase = value
        self.events.on_phrase_change(self._phrase)
