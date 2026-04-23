"""Chauvet Rogue RH1 Hybrid (Intimidator Hybrid 140SR) — DMX 19CH and 13CH.

Implementation module: ``rogue_hybrid_rh1.py``. Channel order matches *Intimidator Hybrid 140SR
User Manual Rev. 1* (Chauvet DJ).

19CH ``Function`` channel (CH 18): QLC+ … 16–23 blackout on color wheel movement;
24–31 blackout on gobo wheel movement (3s hold each per manual).
"""

from __future__ import annotations

import time

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

COLOR_WHEEL = color_wheel_entries_for_fixture_type("chauvet_rogue_hybrid_rh1")

COLOR_WHEEL_ROTATE_MODERATE_DMX = 203

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
    GoboWheelEntry("gobo14", 42),
    GoboWheelEntry("gobo15", 46),
    GoboWheelEntry("gobo16", 49),
    GoboWheelEntry("open", 121),
]

# CH 18 Function — enable blackout-on-wheel-move (midpoints; 3s hold per band).
FUNCTION_BLACKOUT_ON_COLOR_WHEEL_MOVE_DMX = 19
FUNCTION_BLACKOUT_ON_GOBO_WHEEL_MOVE_DMX = 27

STARTUP_FUNCTION_HOLD_SEQUENCE: tuple[tuple[int, float], ...] = (
    (FUNCTION_BLACKOUT_ON_COLOR_WHEEL_MOVE_DMX, 3.0),
    (FUNCTION_BLACKOUT_ON_GOBO_WHEEL_MOVE_DMX, 3.0),
)


class _RogueHybridRH1Base(ChauvetMoverBase):
    """Shared Rogue RH1 Hybrid behavior: rotating-gobo DMX mapping for both personalities."""

    supports_color_wheel_rotate: bool = True
    COLOR_WHEEL_ROTATE_MODERATE_DMX = COLOR_WHEEL_ROTATE_MODERATE_DMX

    _ROTATING_GOBO_DMX: tuple[int, ...] = (6, 14, 20, 26, 32, 38, 44, 50, 58)

    def set_rotating_gobo(self, slot: int, rotate_speed: float = 0.0) -> None:
        """Map (slot, rotate_speed) onto rotating-gobo + gobo_rotation channels."""
        super().set_rotating_gobo(slot, rotate_speed)
        slot_idx = self.rotating_gobo_slot
        if slot_idx >= len(self._ROTATING_GOBO_DMX):
            slot_idx = len(self._ROTATING_GOBO_DMX) - 1
        self.set("rotating_gobo", self._ROTATING_GOBO_DMX[slot_idx])

        speed = self.rotating_gobo_rotate_speed
        if speed == 0.0:
            self.set("gobo_rotation", 0)
        elif speed > 0.0:
            self.set("gobo_rotation", int(round(6 + (116 - 6) * (1.0 - speed))))
        else:
            self.set("gobo_rotation", int(round(121 + (231 - 121) * (-speed))))


class ChauvetRogueHybridRH1_19Ch(_RogueHybridRH1Base):
    """19-channel DMX mode — set fixture to DMX 19CH."""

    STARTUP_FUNCTION_HOLD_SEQUENCE: tuple[tuple[int, float], ...] = STARTUP_FUNCTION_HOLD_SEQUENCE

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
            "chauvet rogue rh1 hybrid 19ch",
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

        self._startup_step = 0
        self._startup_phase_t0: float | None = None
        self._startup_function_complete = False

    def render(self, dmx):
        seq = self.STARTUP_FUNCTION_HOLD_SEQUENCE
        if self._startup_function_complete or not seq:
            super().render(dmx)
            return

        now = time.time()
        if self._startup_phase_t0 is None:
            self._startup_phase_t0 = now
            self.set("function", seq[0][0])
            super().render(dmx)
            return

        _, hold = seq[self._startup_step]
        if now - self._startup_phase_t0 >= hold:
            self._startup_step += 1
            if self._startup_step >= len(seq):
                self._startup_function_complete = True
                self.set("function", 0)
            else:
                self._startup_phase_t0 = now
                self.set("function", seq[self._startup_step][0])

        super().render(dmx)


class ChauvetRogueHybridRH1_13Ch(_RogueHybridRH1Base):
    """13-channel DMX mode — no Function channel; startup wheel-blackout macros are 19CH-only."""

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
            "chauvet rogue rh1 hybrid 13ch",
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