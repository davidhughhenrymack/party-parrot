from typing import List, TypeVar
from parrot.fixtures.base import FixtureBase, FixtureWithBulbs
from parrot.interpreters.base import InterpreterArgs, InterpreterBase
from parrot.interpreters.combo import Combo

T = TypeVar("T")


def group_to_bulbs(group: List[FixtureWithBulbs]) -> List[FixtureBase]:
    bulbs = []
    for fixture in group:
        bulbs.extend(fixture.get_bulbs())
    return bulbs


def for_bulbs(*interpreters: List[InterpreterBase[T]]) -> Combo[T]:

    class ForBulbs(InterpreterBase[T]):
        def __init__(
            self,
            group: List[T],
            args: InterpreterArgs,
        ):
            super().__init__(group, args)
            self.interpreter = Combo(group_to_bulbs(group), args, interpreters)

        @classmethod
        def acceptable(cls, args: InterpreterArgs) -> bool:
            return all([i.acceptable(args) for i in interpreters])

        def step(self, frame, scheme):
            self.interpreter.step(frame, scheme)

        def __str__(self) -> str:
            return f"ForBulbs({str(self.interpreter)})"

    return ForBulbs


class AllBulbs255(InterpreterBase[FixtureWithBulbs]):
    def step(self, frame, scheme):
        for fixture in self.group:
            for bulb in fixture.get_bulbs():
                bulb.set_dimmer(255)
