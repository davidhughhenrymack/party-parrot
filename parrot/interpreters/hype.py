from typing import List, Type, TypeVar

from parrot.director.color_scheme import ColorScheme
from parrot.director.frame import Frame, FrameSignal
from parrot.fixtures.base import FixtureBase
from parrot.interpreters.base import InterpreterArgs, InterpreterBase
from parrot.interpreters.strobe import StrobeHighSustained
from parrot.utils.math import clamp

T = TypeVar("T", bound=FixtureBase)


def hype_switch(
    interp_std: Type[InterpreterBase[T]],
    interp_hype: Type[InterpreterBase[T]],
) -> Type[InterpreterBase[T]]:

    class HypeSwitch(InterpreterBase[T]):
        def __init__(
            self,
            group: List[T],
            args: InterpreterArgs,
        ):
            super().__init__(group, args)

            self.interp_std = interp_std(group, args)
            self.interp_hype = interp_hype(group, args)

            self.hype_on = None

        def step(self, frame: Frame, scheme: ColorScheme):
            if frame[FrameSignal.hype] > 0.5:
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
            return clamp(self.interp_std.get_hype() + 30, 0, 100)

        def __str__(self) -> str:
            return f"{'HypeSwitch(' + str(self.interp_std) + ' | ' + str(self.interp_hype)})"

    return HypeSwitch
