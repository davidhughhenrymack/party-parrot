"""Chauvet Intimidator Hybrid 140SR — DMX personalities 19CH and 13CH.

Implementation module: ``rogue_hybrid_rh1.py``. Channel order and wheel value bands match
*Intimidator Hybrid 140SR User Manual Rev. 1* (Chauvet DJ), pages “DMX Channel Assignments
and Values” (19CH / 13CH).
"""

from __future__ import annotations

from parrot.fixtures.base import GoboWheelEntry
from parrot.fixtures.chauvet.mover_base import ChauvetMoverBase
from parrot.fixtures.color_wheel_library import color_wheel_entries_for_fixture_type
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

# Color wheel — discrete indexed bands; rainbow scroll ranges not modeled as rows.
# Canonical slot list: ``color_wheel_library`` (``chauvet_intimidator_hybrid_140sr``).
COLOR_WHEEL = color_wheel_entries_for_fixture_type("chauvet_intimidator_hybrid_140sr")

# One moderate-speed preset for ``set_color_wheel_rotate(True)`` (188–219 fast→slow).
COLOR_WHEEL_ROTATE_MODERATE_DMX = 203

# Static gobo wheel — 19CH ch 7 / 13CH ch 4 (manual Rev. 1).
STATIC_GOBO_WHEEL: list[GoboWheelEntry] = [
    GoboWheelEntry("open", 1),  # 000–002
    GoboWheelEntry("gobo1", 4),  # 003–005
    GoboWheelEntry("gobo2", 7),  # 006–008
    GoboWheelEntry("gobo3", 10),  # 009–011
    GoboWheelEntry("gobo4", 13),  # 012–014
    GoboWheelEntry("gobo5", 16),  # 015–017
    GoboWheelEntry("gobo6", 19),  # 018–020
    GoboWheelEntry("gobo7", 22),  # 021–023
    GoboWheelEntry("gobo8", 25),  # 024–026
    GoboWheelEntry("gobo9", 28),  # 027–029
    GoboWheelEntry("gobo10", 31),  # 030–032
    GoboWheelEntry("gobo11", 34),  # 033–035
    GoboWheelEntry("gobo12", 37),  # 036–038
    GoboWheelEntry("gobo13", 40),  # 039–041
    GoboWheelEntry("gobo14", 42),  # 040–044
    GoboWheelEntry("gobo15", 46),  # 045–047
    GoboWheelEntry("gobo16", 49),  # 048–050
    GoboWheelEntry("open", 121),  # 115–127 Open
]


class _Hybrid140SRBase(ChauvetMoverBase):
    """Shared Hybrid-140SR behavior: rotating-gobo DMX mapping for both personalities.

    DMX bands from *Intimidator Hybrid 140SR User Manual Rev. 1* (19CH ch 8 / 13CH ch 5).
    """

    supports_color_wheel_rotate: bool = True
    COLOR_WHEEL_ROTATE_MODERATE_DMX = COLOR_WHEEL_ROTATE_MODERATE_DMX

    # Rotating gobo wheel midpoints: 000–011 Open, 012–017 … 054–063 Gobo 8.
    _ROTATING_GOBO_DMX: tuple[int, ...] = (6, 14, 20, 26, 32, 38, 44, 50, 58)

    def set_rotating_gobo(self, slot: int, rotate_speed: float = 0.0) -> None:
        """Map (slot, rotate_speed) onto rotating-gobo + gobo_rotation channels.

        Wheel (ch 8 / 13ch ch 5): Open, then gobos 1–8.
        Rotation (ch 9 / 13ch ch 6): 000–005 no function; 006–116 CW fast→slow;
        121–231 CCW slow→fast; 232–255 bounce.
        """
        super().set_rotating_gobo(slot, rotate_speed)
        slot_idx = self.rotating_gobo_slot
        if slot_idx >= len(self._ROTATING_GOBO_DMX):
            slot_idx = len(self._ROTATING_GOBO_DMX) - 1
        self.set("rotating_gobo", self._ROTATING_GOBO_DMX[slot_idx])

        speed = self.rotating_gobo_rotate_speed
        if speed == 0.0:
            self.set("gobo_rotation", 0)
        elif speed > 0.0:
            # Forward: DMX 6 = fastest … 116 = slowest
            self.set("gobo_rotation", int(round(6 + (116 - 6) * (1.0 - speed))))
        else:
            # Reverse: 121 = slow … 231 = fast
            self.set("gobo_rotation", int(round(121 + (231 - 121) * (-speed))))


class ChauvetIntimidatorHybrid140SR_19Ch(_Hybrid140SRBase):
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


class ChauvetIntimidatorHybrid140SR_13Ch(_Hybrid140SRBase):
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
