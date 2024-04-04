from typing import Type, TypeVar, List
from parrot.interpreters.base import InterpreterBase
from parrot.fixtures.base import FixtureBase
from parrot.director.color_scheme import ColorScheme
from parrot.director.frame import Frame


T = TypeVar("T", bound=FixtureBase)


class Combo(InterpreterBase[T]):

    def __init__(
        self,
        group: List[T],
        interpreters: List[Type[InterpreterBase[T]]],
    ):
        super().__init__(group)
        self.interpreters = [i(group) for i in interpreters]

    def step(self, frame: Frame, scheme: ColorScheme):
        for i in self.interpreters:
            i.step(frame, scheme)

    def __str__(self) -> str:
        return f"{' + '.join([i.__class__.__name__ for i in self.interpreters])} {[str(i) for i in self.group]}"


def combo(*interpreters: List[InterpreterBase[T]]) -> Combo[T]:
    return lambda group: Combo(group, interpreters)
