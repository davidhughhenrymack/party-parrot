"""Disco / mirror ball — single-channel dimmer only."""

from beartype import beartype

from parrot.utils.dmx_utils import Universe
from parrot.fixtures.led_par import Par


@beartype
class Mirrorball(Par):
    """Hanging mirror ball: one DMX channel (dimmer / motor speed proxy)."""

    def __init__(self, patch: int, universe: Universe = Universe.default):
        super().__init__(patch, "mirrorball", 1, universe)

    def set_dimmer(self, value) -> None:
        super().set_dimmer(value)
        self.values[0] = value
