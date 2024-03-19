from typing import List, TypeVar
from parrot.fixtures.base import FixtureBase
from parrot.interpreters.base import InterpreterBase


T = TypeVar("T", bound=FixtureBase)


class Dimmer100(InterpreterBase):
    def step(self, frame, scheme):
        for i in self.group:
            i.set_dimmer(100)


class Dimmer30(InterpreterBase):
    def step(self, frame, scheme):
        for i in self.group:
            i.set_dimmer(30)


class SequenceDimmers(InterpreterBase[T]):
    def __init__(self, group: List[T], dimmer=255, wait_time=1):
        super().__init__(group)
        self.dimmer = dimmer
        self.wait_time = wait_time

    def step(self, frame, scheme):
        for i, fixture in enumerate(self.group):
            fixture.set_dimmer(self.dimmer if frame.time / self.wait_time == i else 0)
