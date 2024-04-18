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

            self.hype_on = None

        def step(self, frame: Frame, scheme: ColorScheme):
            if frame[FrameSignal.hype] > 0.5 and self.interp_std.get_hype() < 70:
                self.interp_hype.step(frame, scheme)
                if self.hype_on != True:
                    self.hype_on = True
                    self.interp_std.exit(frame, scheme)
            else:
                self.interp_std.step(frame, scheme)
                if self.hype_on != False:
                    self.hype_on = False
                    self.interp_hype.exit(frame, scheme)

        def exit(self, frame: Frame, scheme: ColorScheme):
            self.interp_std.exit(frame, scheme)
            self.interp_hype.exit(frame, scheme)

        def get_hype(self):
            return self.interp_std.get_hype()

        def __str__(self) -> str:
            return f"{'HypeSwitch(' + str(self.interp_std) + ' | ' + str(self.interp_hype)})"

    return HypeSwitch
