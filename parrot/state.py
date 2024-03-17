from parrot.interpreters.base import Phrase


class State:

    def __init__(self):
        self._phrase = Phrase.intro_outro

    @property
    def phrase(self):
        return self._phrase

    def set_phrase(self, value: Phrase):
        self._phrase = value
