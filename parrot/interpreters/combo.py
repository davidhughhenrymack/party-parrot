from typing import Generic, TypeVar, List
from parrot.interpreters.base import InterpreterBase
from parrot.fixtures.base import FixtureBase
from parrot.director.color_scheme import ColorScheme
from parrot.director.frame import Frame


T = TypeVar("T", bound=FixtureBase)


class Combo(InterpreterBase[T]):
    def __init__(self, subject: T, interpreters: List[InterpreterBase[T]]):
        super().__init__(subject)
        self.interpreters = [i(subject) for i in interpreters]

    def step(self, frame: Frame, scheme: ColorScheme):
        for i in self.interpreters:
            i.step(frame, scheme)
