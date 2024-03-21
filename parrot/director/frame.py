import time
from typing import Any


class Frame:
    def __init__(self, **kwargs):
        self.time = time.time()
        self.all = kwargs.get("all", 0)
        self.drums = kwargs.get("drums", 0)
        self.bass = kwargs.get("bass", 0)
        self.kwargs = kwargs

    def __getitem__(self, __name: str) -> Any:
        return self.kwargs.get(__name)

    def __str__(self):
        return f"Frame(all={int(self.all* 100)}, drums={int(self.drums* 100)}, bass={int(self.bass* 100)})"

    def __mul__(self, factor):
        return Frame(
            **{k: v * factor for k, v in self.kwargs.items()},
        )
