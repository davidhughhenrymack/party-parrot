import random
from typing import Tuple, Type, TypeVar, List
from parrot.interpreters.base import InterpreterBase
from parrot.fixtures.base import FixtureBase
from parrot.director.color_scheme import ColorScheme
from parrot.director.frame import Frame


T = TypeVar("T", bound=FixtureBase)


def randomize(*interpreters: List[InterpreterBase[T]]) -> InterpreterBase[T]:
    return lambda group: random.choice(interpreters)(group)


def weighted_randomize(
    *interpreters: List[Tuple[int, InterpreterBase[T]]]
) -> InterpreterBase[T]:
    total = sum([i[0] for i in interpreters])
    weights = [i[0] / total for i in interpreters]
    return lambda group: random.choices(interpreters, weights=weights)[0][1](group)
