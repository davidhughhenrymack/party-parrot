import math
import random
from typing import List
from parrot.interpreters.base import InterpreterBase, InterpreterArgs
from parrot.fixtures.base import FixtureBase
from colorama import Fore, Style


class MoveCircles(InterpreterBase):
    def __init__(self, group: List[FixtureBase], args, multiplier=1, phase=None):
        super().__init__(group, args)
        self.multiplier = multiplier

        if phase is None:
            self.phase = random.choice([0, math.pi])
        else:
            self.phase = phase

    def __str__(self):
        return f"🔄 {Fore.GREEN}Circles{Style.RESET_ALL}"

    def step(self, frame, scheme):
        for idx, fixture in enumerate(self.group):
            fixture.set_pan(
                math.cos(frame.time * self.multiplier + self.phase * idx) * 127 + 128
            )
            fixture.set_tilt(
                math.sin(frame.time * self.multiplier + self.phase * idx) * 127 + 128
            )


class MoveNod(InterpreterBase):
    def __init__(self, group: List[FixtureBase], args, multiplier=1, phase=math.pi / 3):
        super().__init__(group, args)
        self.multiplier = multiplier
        self.phase = phase

    def __str__(self):
        return f"⬆️⬇️ {Fore.GREEN}Nod{Style.RESET_ALL}"

    def step(self, frame, scheme):
        for idx, fixture in enumerate(self.group):
            fixture.set_pan(128)
            fixture.set_tilt(
                math.sin(frame.time * self.multiplier + self.phase * idx) * 127 + 128
            )


class MoveFigureEight(InterpreterBase):
    def __init__(self, group: List[FixtureBase], args, multiplier=1, phase=None):
        super().__init__(group, args)
        self.multiplier = multiplier

        if phase is None:
            self.phase = random.choice([0, math.pi])
        else:
            self.phase = phase

    def __str__(self):
        return f"∞ {Fore.GREEN}FigureEight{Style.RESET_ALL}"

    def step(self, frame, scheme):
        for idx, fixture in enumerate(self.group):
            # Figure eight pattern using Lissajous curve
            t = frame.time * self.multiplier + self.phase * idx
            # Scale down the amplitude to keep within 0-255 range
            pan = math.sin(t) * 127 + 128
            tilt = math.sin(2 * t) * 127 + 128
            fixture.set_pan(pan)
            fixture.set_tilt(tilt)


class MoveFan(InterpreterBase):
    def __init__(self, group: List[FixtureBase], args, multiplier=1, spread=1.0):
        super().__init__(group, args)
        self.multiplier = multiplier
        self.spread = spread

    def __str__(self):
        return f"↔️ {Fore.GREEN}Fan{Style.RESET_ALL}"

    def step(self, frame, scheme):
        # Calculate the middle index
        middle_idx = (len(self.group) - 1) / 2

        for idx, fixture in enumerate(self.group):
            # Calculate position relative to middle (-1 to 1)
            rel_pos = (idx - middle_idx) / (middle_idx + 0.00001)
            # Apply sine wave motion with spread
            pan = (
                math.sin(frame.time * self.multiplier) * rel_pos * self.spread * 127
                + 128
            )
            fixture.set_pan(pan)
            # Keep tilt centered
            fixture.set_tilt(128)
