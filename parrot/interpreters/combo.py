from typing import Type, TypeVar
from beartype import beartype
from parrot.interpreters.base import InterpreterArgs, InterpreterBase
from parrot.fixtures.base import FixtureBase
from parrot.director.color_scheme import ColorScheme
from parrot.director.frame import Frame


T = TypeVar("T", bound=FixtureBase)


class Combo(InterpreterBase[T]):
    def __init__(
        self,
        group: list[T],
        args: InterpreterArgs,
        interpreters: list[Type[InterpreterBase[T]]],
    ):
        super().__init__(group, args)
        self.interpreters = [i(group, args) for i in interpreters]

    def step(self, frame: Frame, scheme: ColorScheme):
        for i in self.interpreters:
            i.step(frame, scheme)

    def __str__(self) -> str:
        return f"{' + '.join([str(i) for i in self.interpreters])}"


def combo(*interpreters: list[InterpreterBase[T]]) -> Combo[T]:

    class Combo(InterpreterBase[T]):
        def __init__(
            self,
            group: list[T],
            args: InterpreterArgs,
        ):
            super().__init__(group, args)
            self.interpreters = [i(group, args) for i in interpreters]

        @classmethod
        def acceptable(cls, args: InterpreterArgs) -> bool:
            return all([i.acceptable(args) for i in interpreters])

        def step(self, frame: Frame, scheme: ColorScheme):
            for i in self.interpreters:
                i.step(frame, scheme)

        def exit(self, frame: Frame, scheme: ColorScheme):
            for i in self.interpreters:
                i.exit(frame, scheme)

        def get_hype(self):
            return max([i.get_hype() for i in self.interpreters])

        def __str__(self) -> str:
            return f"{' + '.join([str(i) for i in self.interpreters])}"

    return Combo
