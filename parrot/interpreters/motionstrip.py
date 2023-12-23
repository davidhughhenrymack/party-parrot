import math
from parrot.interpreters.base import InterpreterBase
from parrot.patch.motionstrip import color_to_rgbw, Motionstrip38
from parrot.utils.colour import Color
from parrot.utils.dmx_utils import clamp


class MotionstripWaveform(InterpreterBase[Motionstrip38]):
    def __init__(self, subject: Motionstrip38):
        super().__init__(subject)
        self.signal = "vocals"

    def step(self, frame, scheme):
        color = scheme.fg
        parts = 4

        self.subject.set_pan(math.cos(frame.time) * 127 + 128)

        for i in range(parts):
            low = i * 1 / parts
            value = clamp(frame[self.signal] - low, 0, 1 / parts) * parts

            cc = Color(color, luminance=value)
            self.subject.set_bulb_color(3 - i, cc)
            self.subject.set_bulb_color(i + 4, cc)


class MotionstripSlowRespond(InterpreterBase[Motionstrip38]):
    def __init__(self, subject: Motionstrip38):
        super().__init__(subject)
        self.signal = "vocals"

    def step(self, frame, scheme):
        self.subject.set_pan(math.cos(frame.time) * 127 + 128)
        self.subject.set_color(scheme.fg)
        self.subject.set_dimmer(frame[self.signal] * 255)
