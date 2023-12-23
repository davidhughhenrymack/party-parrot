from typing import List
from parrot.director.frame import Frame
from parrot.patch.led_par import LedPar
from parrot.interpreters.base import InterpreterBase, InterpretorCategory
from parrot.utils.math import lerp
from parrot.director.color_scheme import ColorScheme


class LedParGroup:
    def __init__(self, par_group: List[LedPar]):
        self.par_group = par_group


class LedParSlowRespond(InterpreterBase[LedParGroup]):
    def __init__(self, subject: LedParGroup):
        super().__init__(subject)
        self.dimmer_memory = 0

    def step(self, frame: Frame, scheme: ColorScheme):
        self.dimmer_memory = lerp(self.dimmer_memory, frame.other, 0.5)

        for idx, par in enumerate(self.subject.par_group):
            if idx % 2 == 0:
                par.set_color(scheme.bg)
            else:
                par.set_color(scheme.bg_contrast)

            par.set_dimmer(self.dimmer_memory)

    @classmethod
    def category(cls) -> InterpretorCategory:
        return InterpretorCategory.chill


class LedParSlowDecay(InterpreterBase[LedParGroup]):
    def __init__(self, subject: LedParGroup):
        super().__init__(subject)
        self.dimmer_memory = 0

    def step(self, frame: Frame, scheme: ColorScheme):
        self.dimmer_memory = max(lerp(self.dimmer_memory, 0, 0.1), frame.other)

        for idx, par in enumerate(self.subject.par_group):
            if idx % 2 == 0:
                par.set_color(scheme.bg)
            else:
                par.set_color(scheme.bg_contrast)

            par.set_dimmer(self.dimmer_memory)

    @classmethod
    def category(cls) -> InterpretorCategory:
        return InterpretorCategory.chill
