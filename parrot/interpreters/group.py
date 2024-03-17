from typing import Generic, List, TypeVar, Union
from parrot.fixtures.base import FixtureBase
from parrot.interpreters.base import GroupInterpreterBase, InterpreterBase


T = TypeVar("T", bound=FixtureBase)


class InterpreterGroupify(GroupInterpreterBase[T]):
    def __init__(self, group: List[T], interpreter_cls: type[InterpreterBase[T]]):
        super().__init__(group)
        self.interpreters = [interpreter_cls(subject) for subject in group]

    def step(self, frame, scheme):
        for i in self.interpreters:
            i.step(frame, scheme)


def groupify(interpreter_cls: type[InterpreterBase[T]]) -> InterpreterGroupify[T]:
    return lambda group: InterpreterGroupify(group, interpreter_cls)


def ensure_groupify(
    interpreter_cls: type[Union[InterpreterBase[T], GroupInterpreterBase[T]]]
) -> GroupInterpreterBase[T]:
    if isinstance(interpreter_cls, InterpreterBase):
        return groupify(interpreter_cls)
    else:
        return interpreter_cls


# Type annotation for intepreter map
class FixtureGroup(Generic[T]):
    def __init__(self):
        pass


class SequenceDimmers(GroupInterpreterBase[T]):
    def __init__(self, group: List[T], dimmer=255, wait_time=1):
        super().__init__(group)
        self.dimmer = dimmer
        self.wait_time = wait_time

    def step(self, frame, scheme):
        for i, fixture in enumerate(self.group):
            fixture.set_dimmer(self.dimmer if frame.time / self.wait_time == i else 0)
