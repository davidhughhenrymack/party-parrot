from parrot.interpreters.base import Phrase
from parrot.state import State


class PhraseMachine:
    def __init__(self, state: State):
        self.state = state
        self.drums_since = None

    def step(self, frame):

        if frame["bass"] < 0.1 and self.drums_since == None:
            self.drums_since = frame.time

        if frame["bass"] > 0.2:
            self.drums_since = None

            if self.state.phrase == Phrase.breakdown:
                self.state.set_phrase(Phrase.build)

        if (
            self.drums_since is not None
            and self.state.phrase != Phrase.breakdown
            and frame.time - self.drums_since > 1
        ):
            self.state.set_phrase(Phrase.breakdown)
