import random
from typing import Tuple, Type, TypeVar, List
from parrot.interpreters.base import InterpreterArgs, InterpreterBase, Noop
from parrot.fixtures.base import FixtureBase
from parrot.director.color_scheme import ColorScheme
from parrot.director.frame import Frame
from parrot.interpreters.dimmer import Dimmer0
from parrot.utils.math import clamp


T = TypeVar("T", bound=FixtureBase)


def get_weight(interpreter: Type[InterpreterBase[T]], args: InterpreterArgs) -> float:
    return pow(101 - clamp(abs(interpreter.hype - args.hype), 0, 100), 1.6)


def randomize(*interpreters: List[Type[InterpreterBase[T]]]) -> InterpreterBase[T]:

    class Random(InterpreterBase[T]):
        def __init__(
            self,
            group: List[T],
            args: InterpreterArgs,
        ):
            super().__init__(group, args)

            options = [i for i in interpreters if i.acceptable(args)]
            weights = [get_weight(i, args) for i in options]

            if len(options) == 0:
                self.interpreter = Dimmer0(group, args)
            else:
                self.interpreter = random.choices(options, weights)[0](group, args)

        @classmethod
        def acceptable(cls, args: InterpreterArgs) -> bool:
            return any([i.acceptable(args) for i in interpreters])

        def step(self, frame: Frame, scheme: ColorScheme):
            self.interpreter.step(frame, scheme)

        def exit(self, frame: Frame, scheme: ColorScheme):
            self.interpreter.exit(frame, scheme)

        def get_hype(self):
            return self.interpreter.get_hype()

        def __str__(self) -> str:
            return str(self.interpreter)

    return Random


def weighted_randomize(
    *interpreters: List[Tuple[int, InterpreterBase[T]]]
) -> InterpreterBase[T]:

    class Random(InterpreterBase[T]):
        def __init__(
            self,
            group: List[T],
            args: InterpreterArgs,
        ):
            super().__init__(group, args)

            filtered_interpreters = [i for i in interpreters if i[1].acceptable(args)]

            total = sum([i[0] for i in filtered_interpreters])
            weights = [i[0] / total for i in filtered_interpreters]

            self.interpreter = random.choices(
                [i[1] for i in filtered_interpreters], weights=weights
            )[0](group, args)

        @classmethod
        def acceptable(cls, args: InterpreterArgs) -> bool:
            return any([i[1].acceptable(args) for i in interpreters])

        def step(self, frame: Frame, scheme: ColorScheme):
            self.interpreter.step(frame, scheme)

        def exit(self, frame: Frame, scheme: ColorScheme):
            self.interpreter.exit(frame, scheme)

        def get_hype(self):
            return self.interpreter.get_hype()

        def __str__(self) -> str:
            return str(self.interpreter)

    return Random
