from parrot.director.phrase import Phrase
from parrot.state import State


class PhraseMachine:
    def __init__(self, state: State):
        self.state = state
        self.drums_since = None

    def step(self, frame):

        # if frame["build_rate"] > 1.5:
        #     self.state.set_phrase(Phrase.build)
        #     return

        # if self.state.phrase == Phrase.build and frame["build_rate"] < 0.5:
        #     self.state.set_phrase(Phrase.drop)
        #     return

        return
