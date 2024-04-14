from parrot.director.color_scheme import ColorScheme
from parrot.interpreters.base import InterpreterBase
from parrot.director.frame import Frame, FrameSignal


class StrobeHighSustained(InterpreterBase):
    hype = 90

    def step(self, frame, scheme):
        for i in self.group:
            i.set_strobe(255)

    def exit(self, frame: Frame, scheme: ColorScheme):
        for i in self.group:
            i.set_strobe(0)
