"""Chauvet Intimidator Hybrid 140SR — DMX personalities 19ch and 13ch (user manual Rev. 1)."""

from __future__ import annotations

from parrot.fixtures.base import ColorWheelEntry, GoboWheelEntry
from parrot.fixtures.chauvet.mover_base import ChauvetMoverBase
from parrot.utils.colour import Color
from parrot.utils.dmx_utils import Universe

# 19-channel personality (pan/tilt fine, full feature set)
DMX_LAYOUT_19 = {
    "pan_coarse": 0,
    "pan_fine": 1,
    "tilt_coarse": 2,
    "tilt_fine": 3,
    "speed": 4,
    "color_wheel": 5,
    "gobo_wheel": 6,
    "rotating_gobo": 7,
    "gobo_rotation": 8,
    "prism1": 9,
    "prism2": 10,
    "focus": 11,
    "auto_focus": 12,
    "zoom": 13,
    "frost": 14,
    "dimmer": 15,
    "shutter": 16,
    "function": 17,
    "movement_macros": 18,
}

# 13-channel personality (coarse pan/tilt only; set fixture menu to 13CH)
DMX_LAYOUT_13 = {
    "pan_coarse": 0,
    "tilt_coarse": 1,
    "color_wheel": 2,
    "gobo_wheel": 3,
    "rotating_gobo": 4,
    "gobo_rotation": 5,
    "prism1": 6,
    "prism2": 7,
    "focus": 8,
    "auto_focus": 9,
    "zoom": 10,
    "frost": 11,
    "shutter": 12,
}

# Color wheel channel 6 (19ch) / channel 3 (13ch) — midpoints per manual ranges
COLOR_WHEEL: list[ColorWheelEntry] = [
    ColorWheelEntry(Color("white"), 2),
    ColorWheelEntry(Color("red"), 6),
    ColorWheelEntry(Color("yellow"), 10),
    ColorWheelEntry(Color("green"), 14),
    ColorWheelEntry(Color("#87ceeb"), 18),
    ColorWheelEntry(Color("#e6e6fa"), 22),
    ColorWheelEntry(Color("#ffff99"), 26),
    ColorWheelEntry(Color("blue"), 31),
    ColorWheelEntry(Color("magenta"), 36),
    ColorWheelEntry(Color("lime"), 41),
    ColorWheelEntry(Color("#fff8f0"), 46),
    ColorWheelEntry(Color("#dde8f0"), 51),
    ColorWheelEntry(Color("BlueViolet"), 57),
]

# Static gobo wheel — midpoints of each slot range (manual ch 7 / 13ch ch 4)
STATIC_GOBO_WHEEL: list[GoboWheelEntry] = [
    GoboWheelEntry("open", 1),
    GoboWheelEntry("gobo1", 4),
    GoboWheelEntry("gobo2", 7),
    GoboWheelEntry("gobo3", 10),
    GoboWheelEntry("gobo4", 13),
    GoboWheelEntry("gobo5", 16),
    GoboWheelEntry("gobo6", 19),
    GoboWheelEntry("gobo7", 22),
    GoboWheelEntry("gobo8", 25),
    GoboWheelEntry("gobo9", 28),
    GoboWheelEntry("gobo10", 31),
    GoboWheelEntry("gobo11", 34),
    GoboWheelEntry("gobo12", 37),
    GoboWheelEntry("gobo13", 40),
    GoboWheelEntry("gobo14", 43),
    GoboWheelEntry("gobo15", 46),
    GoboWheelEntry("gobo16", 49),
    GoboWheelEntry("open", 121),
]


class ChauvetIntimidatorHybrid140SR_19Ch(ChauvetMoverBase):
    """19-channel DMX mode — set fixture to DMX 19CH."""

    def __init__(
        self,
        patch: object,
        pan_lower: float = 0.0,
        pan_upper: float = 540.0,
        tilt_lower: float = 0.0,
        tilt_upper: float = 270.0,
        dimmer_upper: float = 255.0,
        universe: Universe = Universe.default,
    ) -> None:
        super().__init__(
            patch,
            "chauvet intimidator hybrid 140sr 19ch",
            19,
            DMX_LAYOUT_19,
            COLOR_WHEEL,
            STATIC_GOBO_WHEEL,
            pan_lower,
            pan_upper,
            tilt_lower,
            tilt_upper,
            dimmer_upper,
            shutter_open=12,
            speed_value=0,
            strobe_shutter_lower=16,
            strobe_shutter_upper=131,
            disable_fine=False,
            universe=universe,
        )
        self.set("function", 0)
        self.set("movement_macros", 0)
        self.set("prism1", 0)
        self.set("prism2", 0)
        self.set("rotating_gobo", 6)
        self.set("gobo_rotation", 0)
        self.set("auto_focus", 0)
        self.set("zoom", 128)
        self.set("frost", 0)


class ChauvetIntimidatorHybrid140SR_13Ch(ChauvetMoverBase):
    """13-channel DMX mode — set fixture to DMX 13CH (no dedicated dimmer channel)."""

    def __init__(
        self,
        patch: object,
        pan_lower: float = 0.0,
        pan_upper: float = 540.0,
        tilt_lower: float = 0.0,
        tilt_upper: float = 270.0,
        dimmer_upper: float = 255.0,
        universe: Universe = Universe.default,
    ) -> None:
        super().__init__(
            patch,
            "chauvet intimidator hybrid 140sr 13ch",
            13,
            DMX_LAYOUT_13,
            COLOR_WHEEL,
            STATIC_GOBO_WHEEL,
            pan_lower,
            pan_upper,
            tilt_lower,
            tilt_upper,
            dimmer_upper,
            shutter_open=12,
            speed_value=0,
            strobe_shutter_lower=16,
            strobe_shutter_upper=131,
            disable_fine=True,
            universe=universe,
        )
        self.set("prism1", 0)
        self.set("prism2", 0)
        self.set("rotating_gobo", 6)
        self.set("gobo_rotation", 0)
        self.set("auto_focus", 0)
        self.set("zoom", 128)
        self.set("frost", 0)
