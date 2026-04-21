"""Chauvet Rogue Beam R2 / Rogue R2X Beam — DMX matches *Rogue R2X Beam User Manual Rev. 1* (19CH).

Physical product may be labeled R2 or R2X; wheel layouts and 19-channel map follow the R2X manual.
"""

from __future__ import annotations

import time

from parrot.fixtures.base import GoboWheelEntry
from parrot.fixtures.chauvet.mover_base import ChauvetMoverBase
from parrot.fixtures.color_wheel_library import color_wheel_entries_for_fixture_type
from parrot.utils.dmx_utils import Universe

# --- 19CH personality (manual “DMX Values → 19CH”) — channel indices 0-based ---
DMX_LAYOUT_19 = {
    "pan_coarse": 0,
    "pan_fine": 1,
    "tilt_coarse": 2,
    "tilt_fine": 3,
    "speed": 4,
    "dimmer": 5,
    "dimmer_fine": 6,
    "shutter": 7,
    "color_wheel": 8,
    "gobo_wheel": 9,
    "prism1": 10,
    "prism1_rotate": 11,
    "prism2": 12,
    "prism2_rotate": 13,
    "focus": 14,
    "frost": 15,
    "auto_program": 16,
    "auto_speed": 17,
    "control": 18,
}

# Channel 9 — indexed slots + scroll bands in manual; discrete rows live in
# ``parrot.fixtures.color_wheel_library`` (key ``chauvet_rogue_beam_r2``).
COLOR_WHEEL = color_wheel_entries_for_fixture_type("chauvet_rogue_beam_r2")

# Channel 10 — static gobo wheel (17 gobos + open + open); midpoints per manual.
GOBO_WHEEL: list[GoboWheelEntry] = [
    GoboWheelEntry("open", 1),  # 000–003
    GoboWheelEntry("gobo1", 5),  # 004–006 Gobo 1
    GoboWheelEntry("gobo2", 8),  # 007–009
    GoboWheelEntry("gobo3", 11),  # 010–012
    GoboWheelEntry("gobo4", 14),  # 013–015
    GoboWheelEntry("gobo5", 17),  # 016–018
    GoboWheelEntry("gobo6", 20),  # 019–021
    GoboWheelEntry("gobo7", 23),  # 022–024
    GoboWheelEntry("gobo8", 26),  # 025–027
    GoboWheelEntry("gobo9", 29),  # 028–030
    GoboWheelEntry("gobo10", 32),  # 031–033
    GoboWheelEntry("gobo11", 35),  # 034–036
    GoboWheelEntry("gobo12", 38),  # 037–039
    GoboWheelEntry("gobo13", 41),  # 040–042
    GoboWheelEntry("gobo14", 44),  # 043–045
    GoboWheelEntry("gobo15", 47),  # 046–048
    GoboWheelEntry("gobo16", 50),  # 049–051
    GoboWheelEntry("gobo17", 53),  # 052–055
    GoboWheelEntry("open", 57),  # 056–059 Open
]

# Clockwise color scroll 128–189 (fast→slow); one moderate-speed preset for API use.
COLOR_WHEEL_ROTATE_MODERATE_DMX = 158


class ChauvetRogueBeamR2(ChauvetMoverBase):
    """Rogue R2X Beam @ 19CH — preview skips prism/focus visuals; DMX still carries those channels."""

    supports_prism: bool = False
    supports_focus: bool = False
    supports_color_wheel_rotate: bool = True
    COLOR_WHEEL_ROTATE_MODERATE_DMX = COLOR_WHEEL_ROTATE_MODERATE_DMX

    def __init__(
        self,
        patch,
        pan_lower=270,
        pan_upper=450,
        tilt_lower=0,
        tilt_upper=90,
        # Manual ch 6: Dimmer 000–255 (0–100%); no cap in the R2X spec.
        dimmer_upper=255,
        universe=Universe.default,
    ):
        super().__init__(
            patch=patch,
            name="chauvet rogue beam r2",
            width=19,
            dmx_layout=DMX_LAYOUT_19,
            color_wheel=COLOR_WHEEL,
            gobo_wheel=GOBO_WHEEL,
            pan_lower=pan_lower,
            pan_upper=pan_upper,
            tilt_lower=tilt_lower,
            tilt_upper=tilt_upper,
            dimmer_upper=dimmer_upper,
            shutter_open=12,  # 008–015 Open (primary)
            speed_value=0,
            universe=universe,
            strobe_shutter_lower=16,
            strobe_shutter_upper=131,
            disable_fine=False,
        )

        self.control_disable_blackout_on_all_fn = 85  # 3 sec hold
        self.control_lamp_on = 135  # 1 sec hold
        self.set("control", self.control_disable_blackout_on_all_fn)

        self.set("dimmer_fine", 0)
        self.set("prism1", 0)
        self.set("prism1_rotate", 0)
        self.set("prism2", 0)
        self.set("prism2_rotate", 0)
        self.set("auto_program", 0)
        self.set("auto_speed", 0)
        self.set("frost", 0)
        self.set("focus", 0)

        self._startup_sequence_started = False
        self._startup_sequence_complete = False
        self._startup_sequence_start_time = None

    def render(self, dmx):
        if not self._startup_sequence_complete:
            current_time = time.time()

            if not self._startup_sequence_started:
                self._startup_sequence_started = True
                self._startup_sequence_start_time = current_time
                self.set("control", self.control_lamp_on)

            elif current_time - self._startup_sequence_start_time >= 1:
                self.set("control", self.control_disable_blackout_on_all_fn)

            if current_time - self._startup_sequence_start_time >= 4:
                self._startup_sequence_complete = True
                self.set("control", 0)

        super().render(dmx)
