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


class Dimmer0(InterpreterBase):
    def step(self, frame, scheme):
        for i in self.group:
            i.set_dimmer(0)


class SequenceDimmers(InterpreterBase[T]):
    def __init__(self, group: List[T], dimmer=255, wait_time=60 * 2 / 120):
        super().__init__(group)
        self.dimmer = dimmer
        self.wait_time = wait_time

    def step(self, frame, scheme):
        for i, fixture in enumerate(self.group):
            fixture.set_dimmer(
                self.dimmer
                if round(frame.time / self.wait_time) % len(self.group) == i
                else 0
            )
