"""Chauvet Rogue R2 Beam — DMX matches *Rogue R2 Beam User Manual Rev. 2* (18CH personality).

The shipping R2 Beam exposes only 15CH and 18CH personalities; we target 18CH for fine
dimmer + movement-macro channels. The fixture has a single 8-facet rotating prism plus a
separate prism zoom channel (NOT two prisms — that was the older 19CH R2X interpretation).

Control channel (CH 18) blackout-while-moving bands per manual:
- 090–099 blackout while color wheel moving (3 sec hold)
- 110–119 blackout while gobo wheels moving (3 sec hold)
- 130–139 lamp on (~1 sec hold)
"""

from __future__ import annotations

from parrot.fixtures.base import GoboWheelEntry
from parrot.fixtures.chauvet.mover_base import ChauvetMoverBase
from parrot.fixtures.color_wheel_library import color_wheel_entries_for_fixture_type
from parrot.utils.dmx_utils import Universe

# --- 18CH personality (manual “DMX Values → 18CH”) — channel indices 0-based ---
DMX_LAYOUT_18 = {
    "pan_coarse": 0,        # CH 1  Pan
    "pan_fine": 1,          # CH 2  Fine Pan
    "tilt_coarse": 2,       # CH 3  Tilt
    "tilt_fine": 3,         # CH 4  Fine Tilt
    "speed": 4,             # CH 5  Pan/Tilt Speed
    "dimmer": 5,            # CH 6  Dimmer
    "dimmer_fine": 6,       # CH 7  Fine Dimmer
    "shutter": 7,           # CH 8  Shutter
    "color_wheel": 8,       # CH 9  Color Wheel (14 colors + open + split/scroll)
    "gobo_wheel": 9,        # CH 10 Gobo Wheel (17 gobos + open + shake/scroll)
    "prism1": 10,           # CH 11 Prism (no-prism 000–004 / insert 005–255)
    "prism1_rotate": 11,    # CH 12 Prism Rotate (index / CCW fast→slow / stop / CW slow→fast)
    "prism_zoom": 12,       # CH 13 Prism Zoom (000–255 0–100%)
    "focus": 13,            # CH 14 Focus
    "frost": 14,            # CH 15 Frost
    "auto_program": 15,     # CH 16 Movement Macros (31 effects + no function)
    "auto_speed": 16,       # CH 17 Movement Macro Speed
    "control": 17,          # CH 18 Control (dimmer mode, P/T mode, blackouts, lamp, resets)
}

# Channel 9 — indexed slots + scroll bands in manual; discrete rows live in
# ``parrot.fixtures.color_wheel_library`` (canonical key ``chauvet_rogue_beam_r2x``).
COLOR_WHEEL = color_wheel_entries_for_fixture_type("chauvet_rogue_beam_r2x")

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

# CH 18 Control — lamp + wheel blackout selects. Values are the midpoints of
# the manual's bands; each macro is a *latching* option that the fixture
# remembers across power cycles once the band is held for ~3s (~1s for lamp).
CONTROL_LAMP_ON_DMX = 135  # 130–139 Lamp on (~1s hold)
CONTROL_BLACKOUT_ON_COLOR_WHEEL_MOVE_DMX = 95  # 90–99 Blackout while color wheel moving (3s hold)
CONTROL_BLACKOUT_ON_GOBO_WHEELS_MOVE_DMX = 115  # 110–119 Blackout while gobo wheels moving (3s hold)

# On boot we hold each macro on CH 18 long enough for the fixture to latch it,
# then park the channel at 0. Order matters only insofar as each (value, hold)
# pair must be on the wire continuously for at least its hold duration; the
# render loop keeps writing the same value between advances. Result after
# startup: lamp struck, color-wheel changes blackout in-flight, gobo-wheel
# changes blackout in-flight — so transitions snap cleanly without color/gobo
# "scrolls" being visible to the audience.
STARTUP_CONTROL_HOLD_SEQUENCE: tuple[tuple[int, float], ...] = (
    (CONTROL_LAMP_ON_DMX, 1.0),
    (CONTROL_BLACKOUT_ON_COLOR_WHEEL_MOVE_DMX, 3.0),
    (CONTROL_BLACKOUT_ON_GOBO_WHEELS_MOVE_DMX, 3.0),
)


class ChauvetRogueBeamR2X(ChauvetMoverBase):
    """Rogue R2 Beam @ 18CH — preview skips prism/focus visuals; DMX still carries those channels.

    Class name kept as ``ChauvetRogueBeamR2X`` to avoid churning callers / fixture catalog
    keys (``chauvet_rogue_beam_r2x``). The wire format now matches the R2 Beam Rev. 2 manual,
    which is what ships in the box (R2X 19CH was never quite right for this hardware).
    """

    supports_prism: bool = False
    supports_focus: bool = False
    supports_color_wheel_rotate: bool = True
    COLOR_WHEEL_ROTATE_MODERATE_DMX = COLOR_WHEEL_ROTATE_MODERATE_DMX

    STARTUP_CONTROL_HOLD_SEQUENCE: tuple[tuple[int, float], ...] = STARTUP_CONTROL_HOLD_SEQUENCE

    def __init__(
        self,
        patch,
        pan_lower=270,
        pan_upper=450,
        tilt_lower=0,
        tilt_upper=90,
        dimmer_upper=255,
        universe=Universe.default,
    ):
        super().__init__(
            patch=patch,
            name="chauvet rogue beam r2",
            width=18,
            dmx_layout=DMX_LAYOUT_18,
            color_wheel=COLOR_WHEEL,
            gobo_wheel=GOBO_WHEEL,
            pan_lower=pan_lower,
            pan_upper=pan_upper,
            tilt_lower=tilt_lower,
            tilt_upper=tilt_upper,
            dimmer_upper=dimmer_upper,
            shutter_open=12,
            speed_value=0,
            universe=universe,
            strobe_shutter_lower=16,
            strobe_shutter_upper=131,
            disable_fine=False,
        )

        self.set("dimmer_fine", 0)
        self.set("prism1", 0)
        self.set("prism1_rotate", 0)
        self.set("prism_zoom", 0)
        self.set("auto_program", 0)
        self.set("auto_speed", 0)
        self.set("frost", 0)
        self.set("focus", 0)
