import enum
import time
from typing import Any, Union
from beartype import beartype
import numpy as np


@beartype
class FrameSignal(enum.Enum):
    freq_all = "freq_all"
    freq_high = "freq_high"
    freq_low = "freq_low"
    sustained_low = "sustained_low"
    sustained_high = "sustained_high"
    strobe = "strobe"
    big_blinder = "big_blinder"
    small_blinder = "small_blinder"
    pulse = "pulse"
    dampen = "dampen"


@beartype
class Frame:
    def __init__(
        self,
        values: dict[FrameSignal, float],
        timeseries: dict[str, Union[list[float], np.ndarray]] = {},
    ):
        self.time = time.perf_counter()
        self.values = values
        self.timeseries: dict[str, Union[list[float], np.ndarray]] = timeseries

    def extend(self, additional_signals: dict[FrameSignal, float]):
        self.values.update(additional_signals)

    def __getitem__(self, __name: FrameSignal | str) -> Any:
        if isinstance(__name, FrameSignal):
            return self.values.get(__name, 0.0)
        return self.values.get(__name, 0.0)

    def __mul__(self, factor):
        return Frame({k: v * factor for k, v in self.values.items()}, self.timeseries)
