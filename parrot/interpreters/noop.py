from parrot.fixtures.base import FixtureBase
from parrot.interpreters.base import InterpreterBase


class Noop(InterpreterBase[FixtureBase]):
    def __init__(self, fixture):
        self.fixture = fixture

    def step(self, frame, scheme):
        pass
