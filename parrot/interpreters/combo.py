from typing import Generic, TypeVar, List, Union
from parrot.interpreters.base import GroupInterpreterBase, InterpreterBase
from parrot.fixtures.base import FixtureBase
from parrot.director.color_scheme import ColorScheme
from parrot.director.frame import Frame
from parrot.interpreters.group import ensure_groupify


T = TypeVar("T", bound=FixtureBase)


class Combo(InterpreterBase[T]):
    def __init__(self, subject: T, interpreters: List[InterpreterBase[T]]):
        super().__init__(subject)
        self.interpreters = [i(subject) for i in interpreters]

    def step(self, frame: Frame, scheme: ColorScheme):
        for i in self.interpreters:
            i.step(frame, scheme)


def comboify(interpreters: List[InterpreterBase[T]]) -> Combo[T]:
    return lambda subject: Combo(subject, interpreters)


class GroupCombo(GroupInterpreterBase[T]):

    def __init__(
        self,
        group: List[T],
        interpreters: List[Union[InterpreterBase, GroupInterpreterBase[T]]],
    ):
        super().__init__(group)
        self.interpreters = [ensure_groupify(i)(group) for i in interpreters]

    def step(self, frame: Frame, scheme: ColorScheme):
        for i in self.interpreters:
            i.step(frame, scheme)


def group_comboify(
    interpreters: List[Union[InterpreterBase, GroupInterpreterBase[T]]]
) -> GroupCombo[T]:
    return lambda group: GroupCombo(group, interpreters)
