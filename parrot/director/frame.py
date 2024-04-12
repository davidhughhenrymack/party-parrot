import enum
import time
from typing import Any


class FrameSignal(enum.Enum):
    freq_all = "freq_all"
    freq_high = "freq_high"
    freq_low = "freq_low"
    sustained_low = "sustained_low"


class Frame:
    def __init__(self, values):
        self.time = time.time()
        self.all = values.get(FrameSignal.freq_all, 0)
        self.drums = values.get(FrameSignal.freq_high, 0)
        self.bass = values.get(FrameSignal.freq_low, 0)
        self.values = values

    def __getitem__(self, __name: str) -> Any:
        return self.values.get(__name)

    def __str__(self):
        return f"Frame(all={int(self.all* 100)}, drums={int(self.drums* 100)}, bass={int(self.bass* 100)})"

    def __mul__(self, factor):
        return Frame(
            {k: v * factor for k, v in self.values.items()},
        )
