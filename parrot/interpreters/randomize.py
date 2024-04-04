import random
from typing import Type, TypeVar, List
from parrot.interpreters.base import InterpreterBase
from parrot.fixtures.base import FixtureBase
from parrot.director.color_scheme import ColorScheme
from parrot.director.frame import Frame


T = TypeVar("T", bound=FixtureBase)


def randomize(*interpreters: List[InterpreterBase[T]]) -> InterpreterBase[T]:
    return lambda group: random.choice(interpreters)(group)
