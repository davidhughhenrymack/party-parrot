"""Disco / mirror ball — dimmer + RGB (4-channel: dimmer, r, g, b).

The fixture historically was a single-channel dimmer, but we want to tint the
reflected sparkles, so the DMX footprint is now ``[dimmer, r, g, b]``. Runtime
and web renderers both read the fixture's color for the beam tint.
"""

from beartype import beartype

from parrot.utils.colour import Color
from parrot.utils.dmx_utils import Universe
from parrot.fixtures.led_par import Par


@beartype
class Mirrorball(Par):
    """Hanging mirror ball: 4 DMX channels — dimmer, r, g, b."""

    def __init__(self, patch: int, universe: Universe = Universe.default):
        super().__init__(patch, "mirrorball", 4, universe)

    def set_dimmer(self, value) -> None:
        super().set_dimmer(value)
        self.values[0] = value

    def set_color(self, color: Color) -> None:
        super().set_color(color)
        self.values[1] = color.red * 255
        self.values[2] = color.green * 255
        self.values[3] = color.blue * 255
