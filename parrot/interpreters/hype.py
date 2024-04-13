from typing import List, Type, TypeVar

from parrot.director.color_scheme import ColorScheme
from parrot.director.frame import Frame, FrameSignal
from parrot.fixtures.base import FixtureBase
from parrot.interpreters.base import InterpreterArgs, InterpreterBase

T = TypeVar("T", bound=FixtureBase)


def hype_switch(interpreter: Type[InterpreterBase[T]]) -> Type[InterpreterBase[T]]:

    class HypeSwitch(InterpreterBase[T]):
        def __init__(
            self,
            group: List[T],
            args: InterpreterArgs,
        ):
            super().__init__(group, args)

            self.interp_std = interpreter(group, args)
            self.interp_hype = interpreter(
                group, InterpreterArgs(95, args.allow_rainbows)
            )

        def step(self, frame: Frame, scheme: ColorScheme):
            if frame[FrameSignal.hype] > 0.5:
                self.interp_hype.step(frame, scheme)
            else:
                self.interp_std.step(frame, scheme)

    return HypeSwitch
