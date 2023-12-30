import math
from parrot.interpreters.base import InterpreterBase
from parrot.patch.motionstrip import color_to_rgbw, Motionstrip38
from parrot.utils.colour import Color
from parrot.utils.dmx_utils import clamp
from parrot.utils.lerp import lerp


class MotionstripWaveform(InterpreterBase[Motionstrip38]):
    def __init__(self, subject: Motionstrip38):
        super().__init__(subject)
        self.signal = "vocals"

    def step(self, frame, scheme):
        color = scheme.fg
        parts = 4
        self.subject.set_dimmer(255)

        self.subject.set_pan(math.cos(frame.time) * 127 + 128)

        for i in range(parts):
            low = i * 1 / parts
            value = clamp(frame[self.signal] - low, 0, 1 / parts) * parts

            cc = Color(color)
            cc.set_rgb((cc.red * value, cc.green * value, cc.blue * value))
            self.subject.set_bulb_color(3 - i, cc)
            self.subject.set_bulb_color(i + 4, cc)


class MotionstripSlowRespond(InterpreterBase[Motionstrip38]):
    def __init__(self, subject: Motionstrip38):
        super().__init__(subject)
        self.signal = "sustained"
        self.dimmer_memory = 0
        self.decay_rate = 0.24

    def step(self, frame, scheme):
        self.subject.set_pan(math.cos(frame.time) * 127 + 128)

        if frame[self.signal] > 0.2:
            self.dimmer_memory = lerp(
                self.dimmer_memory, frame[self.signal] * 255, self.decay_rate
            )
        else:
            self.dimmer_memory = lerp(self.dimmer_memory, 0, self.decay_rate)

        # print(self.dimmer_memory)

        if frame[self.signal] > 0.6:
            self.subject.set_color(scheme.fg)
            self.subject.set_dimmer(255 * math.sin(frame.time * 30))
        elif frame[self.signal] > 0.4:
            self.render_bulb_chase(frame, scheme)
            self.subject.set_dimmer(255)
        else:
            self.subject.set_color(scheme.fg)
            self.subject.set_dimmer(self.dimmer_memory)

    def render_bulb_chase(self, frame, scheme):
        for i in range(8):
            color = Color("black")
            if int(frame.time * 10) % 8 == i:
                color = scheme.fg
            self.subject.set_bulb_color(i, color)
