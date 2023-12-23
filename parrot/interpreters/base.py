from enum import Enum
from typing import Generic, TypeVar
from parrot.director.frame import Frame
from parrot.patch.base import FixtureBase
from parrot.director.color_scheme import ColorScheme

InterpretorCategory = Enum("InterpretorCategory", ["hype", "chill"])

T = TypeVar("T", bound=FixtureBase)


class InterpreterBase(Generic[T]):
    def __init__(self, subject: T):
        self.subject = subject

    def step(self, frame: Frame, scheme: ColorScheme):
        pass

    @classmethod
    def category(cls) -> InterpretorCategory:
        pass
