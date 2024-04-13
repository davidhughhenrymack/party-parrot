import enum
import time
from typing import Any


class FrameSignal(enum.Enum):
    freq_all = "freq_all"
    freq_high = "freq_high"
    freq_low = "freq_low"
    sustained_low = "sustained_low"
    sustained_high = "sustained_high"
    hype = "hype"


class Frame:
    def __init__(self, values: dict[FrameSignal, float]):
        self.time = time.perf_counter()
        self.values = values

    def extend(self, additional_signals: dict[FrameSignal, float]):
        self.values.update(additional_signals)

    def __getitem__(self, __name: str) -> Any:
        return self.values.get(__name)

    def __mul__(self, factor):
        return Frame(
            {k: v * factor for k, v in self.values.items()},
        )
