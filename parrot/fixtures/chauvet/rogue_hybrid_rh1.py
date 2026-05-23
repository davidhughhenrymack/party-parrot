"""Chauvet Rogue™ RH1 Hybrid — DMX 20CH (default) and 25CH personalities.

Implementation module: ``rogue_hybrid_rh1.py``. Channel order matches the
*Rogue™ RH1 Hybrid User Manual Rev. 4* (Chauvet Professional, Sept 2015).

The real fixture only ships two personalities: 20CH and 25CH. The 25CH layout
adds Fine Dimmer, Fine Focus, Fine Zoom, and two Movement-Macro channels
between the 20CH channels — every other slot keeps the same role.

CH 20 (Control) blackout macros — used by the startup hold sequence below:
    090–099 Blackout while color wheel moving (3 sec hold)
    110–119 Blackout while gobo wheels moving (3 sec hold)
    130–139 Lamp on
    230–239 Lamp off
"""

from __future__ import annotations

from parrot.fixtures.base import GoboWheelEntry
from parrot.fixtures.chauvet.mover_base import ChauvetMoverBase
from parrot.fixtures.color_wheel_library import color_wheel_entries_for_fixture_type
from parrot.utils.dmx_utils import Universe

# 20-channel personality (Rev. 4 manual, page 27). 0-based DMX layout.
DMX_LAYOUT_20 = {
    "pan_coarse": 0,  # CH 1  Pan
    "pan_fine": 1,  # CH 2  Fine Pan
    "tilt_coarse": 2,  # CH 3  Tilt
    "tilt_fine": 3,  # CH 4  Fine Tilt
    "speed": 4,  # CH 5  Pan/Tilt Speed
    "dimmer": 5,  # CH 6  Dimmer
    "shutter": 6,  # CH 7  Shutter
    "color_wheel": 7,  # CH 8  Color Wheel
    "gobo_wheel": 8,  # CH 9  Gobo Wheel 1 (static, 13 gobos + open)
    "rotating_gobo": 9,  # CH 10 Gobo Wheel 2 (rotating, 9 gobos + open)
    "gobo_rotation": 10,  # CH 11 Gobo Wheel 2 Rotate
    "focus": 11,  # CH 12 Focus
    "zoom": 12,  # CH 13 Zoom
    "prism1": 13,  # CH 14 Prism 1 (6-facet insert on/off)
    "prism1_rotate": 14,  # CH 15 Prism 1 Rotate
    "prism2": 15,  # CH 16 Prism 2 (8-facet insert on/off)
    "prism2_rotate": 16,  # CH 17 Prism 2 Rotate
    "frost": 17,  # CH 18 Frost
    "beam_diffraction": 18,  # CH 19 Beam Diffraction
    "control": 19,  # CH 20 Control (blackout macros, lamp on/off, resets)
}

# 25-channel personality (Rev. 4 manual, page 22). Adds Fine Dimmer (CH 7),
# Fine Focus (CH 14), Fine Zoom (CH 16), Movement Macros (CH 23) and
# Movement Macro Speed (CH 24) to the 20CH set.
DMX_LAYOUT_25 = {
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
    "rotating_gobo": 10,
    "gobo_rotation": 11,
    "focus": 12,
    "focus_fine": 13,
    "zoom": 14,
    "zoom_fine": 15,
    "prism1": 16,
    "prism1_rotate": 17,
    "prism2": 18,
    "prism2_rotate": 19,
    "frost": 20,
    "beam_diffraction": 21,
    "movement_macros": 22,
    "movement_macro_speed": 23,
    "control": 24,
}

COLOR_WHEEL = color_wheel_entries_for_fixture_type("chauvet_rogue_hybrid_rh1")

# Color-wheel scroll plateau (CW slow → 188, fast → 219 per manual). Pick the
# middle of the band so the rainbow effect runs at a steady pace.
COLOR_WHEEL_ROTATE_MODERATE_DMX = 203

# CH 7 / CH 8 Shutter: manual strobe band is 016–131 (slow → fast). The top of
# that range is too frantic for the RH1 in this rig, so cap interpreter strobe
# requests to the slower lower-middle of the band.
SLOW_STROBE_SHUTTER_UPPER_DMX = 64

# Gobo Wheel 1 (static, CH 9 in 20CH). Manual midpoints: 13 gobos + open;
# the wide 043–059 "Open" band is included so interpreters can ask for "open"
# explicitly without colliding with the gobo-shake bands above 060.
STATIC_GOBO_WHEEL: list[GoboWheelEntry] = [
    GoboWheelEntry("open", 1),
    GoboWheelEntry("gobo1", 5),
    GoboWheelEntry("gobo2", 8),
    GoboWheelEntry("gobo3", 11),
    GoboWheelEntry("gobo4", 14),
    GoboWheelEntry("gobo5", 17),
    GoboWheelEntry("gobo6", 20),
    GoboWheelEntry("gobo7", 23),
    GoboWheelEntry("gobo8", 26),
    GoboWheelEntry("gobo9", 29),
    GoboWheelEntry("gobo10", 32),
    GoboWheelEntry("gobo11", 35),
    GoboWheelEntry("gobo12", 38),
    GoboWheelEntry("gobo13", 41),
    GoboWheelEntry("open", 51),
]

# CH 20 Control — startup macros that strike the lamp and latch the fixture
# into "blackout while wheel is moving" for both wheels. Hold each code long
# enough for the fixture to latch it, then park control at 0 ("No function").
CONTROL_BLACKOUT_ON_COLOR_WHEEL_MOVE_DMX = 95  # 090–099 band
CONTROL_BLACKOUT_ON_GOBO_WHEEL_MOVE_DMX = 115  # 110–119 band
CONTROL_LAMP_ON_DMX = 135  # 130–139 Lamp on

STARTUP_CONTROL_HOLD_SEQUENCE: tuple[tuple[int, float], ...] = (
    (CONTROL_LAMP_ON_DMX, 1.0),
    (CONTROL_BLACKOUT_ON_COLOR_WHEEL_MOVE_DMX, 3.0),
    (CONTROL_BLACKOUT_ON_GOBO_WHEEL_MOVE_DMX, 3.0),
)


class _RogueHybridRH1Base(ChauvetMoverBase):
    """Shared Rogue RH1 Hybrid behavior: rotating-gobo + split prism channels.

    The Rev. 4 manual splits each prism into two separate DMX channels
    (insert on/off + rotate), so we override ``set_prism`` to write both.
    """

    supports_color_wheel_rotate: bool = True
    COLOR_WHEEL_ROTATE_MODERATE_DMX = COLOR_WHEEL_ROTATE_MODERATE_DMX

    # Gobo Wheel 2 (rotating) slot → DMX midpoint, per Rev. 4 manual.
    # Index 0 = open (CH 10 value 000), indices 1..9 = Gobo 1..9.
    _ROTATING_GOBO_DMX: tuple[int, ...] = (0, 8, 14, 20, 26, 32, 38, 44, 50, 58)

    def set_rotating_gobo(self, slot: int, rotate_speed: float = 0.0) -> None:
        """Map (slot, rotate_speed) onto Gobo Wheel 2 + Gobo Wheel 2 Rotate.

        Rotation band on CH 11 (Rev. 4 manual):
            000–063  Gobo index (static)
            064–147  Clockwise rotation, slow → fast
            148–231  Counter-clockwise rotation, fast → slow
            232–255  Clockwise / counter-clockwise sweep
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
            # Forward (CW) band: 64 (slow) → 147 (fast)
            self.set("gobo_rotation", int(round(64 + (147 - 64) * speed)))
        else:
            # Reverse (CCW) band per manual: 148 (fast) → 231 (slow). Match
            # the "slow → fast" feel of -1.0 = fast by inverting the ramp so
            # speed=-1 lands near 148 (fastest CCW) and speed≈0 lands near 231.
            self.set("gobo_rotation", int(round(148 + (231 - 148) * (1.0 + speed))))

    def set_prism(self, on: bool, rotate_speed: float = 0.0) -> None:
        """Set Prism 1 insert + rotation per the Rev. 4 manual.

        CH 14 Prism 1: 000–004 no function, 005–255 prism insert.
        CH 15 Prism 1 Rotate: 000–127 indexed (static), 128–189 CW fast→slow,
        190–193 stop, 194–255 CCW slow→fast.
        """
        # Updates `prism_on` + `prism_rotate_speed` on MovingHead (with clamp).
        from parrot.fixtures.moving_head import MovingHead

        MovingHead.set_prism(self, on, rotate_speed)

        if not self.prism_on:
            self.set("prism1", 0)
            self.set("prism1_rotate", 0)
            self.set("prism2", 0)
            self.set("prism2_rotate", 0)
            return

        # Insert the prism — value within the wide 005–255 plateau.
        self.set("prism1", 255)
        self.set("prism2", 255)

        speed = self.prism_rotate_speed
        if speed == 0.0:
            # Static prism — Index/stop on the rotate channel.
            self.set("prism1_rotate", 0)
            self.set("prism2_rotate", 0)
        elif speed > 0.0:
            # Forward rotation band on CH 15: 128 (fast) → 189 (slow).
            # speed = 1.0 should be the fastest, so map 1.0 → 128, 0.0+ → 189.
            self.set("prism1_rotate", int(round(189 - (189 - 128) * speed)))
            self.set("prism2_rotate", int(round(189 - (189 - 128) * speed)))
        else:
            # Reverse rotation band on CH 15: 194 (slow) → 255 (fast).
            self.set("prism1_rotate", int(round(194 + (255 - 194) * (-speed))))
            self.set("prism2_rotate", int(round(194 + (255 - 194) * (-speed))))


class ChauvetRogueHybridRH1_20Ch(_RogueHybridRH1Base):
    """20-channel DMX mode — set fixture menu to ``DMX 20CH`` (Rev. 4 default)."""

    STARTUP_CONTROL_HOLD_SEQUENCE: tuple[tuple[int, float], ...] = (
        STARTUP_CONTROL_HOLD_SEQUENCE
    )

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
            "chauvet rogue rh1 hybrid",
            20,
            DMX_LAYOUT_20,
            COLOR_WHEEL,
            STATIC_GOBO_WHEEL,
            pan_lower,
            pan_upper,
            tilt_lower,
            tilt_upper,
            dimmer_upper,
            # Shutter "Open" band per Rev. 4 manual is 008–015; pick the middle.
            shutter_open=12,
            speed_value=0,
            # Strobe band per manual is 016–131 (slow → fast), but cap our
            # interpreter-driven strobe lower so held remote strobe is usable.
            strobe_shutter_lower=16,
            strobe_shutter_upper=SLOW_STROBE_SHUTTER_UPPER_DMX,
            disable_fine=False,
            universe=universe,
        )
        # Park optional channels at sensible defaults so the fixture isn't left
        # in random states on first frame.
        self.set("control", 0)
        self.set("prism1", 0)
        self.set("prism1_rotate", 0)
        self.set("prism2", 0)
        self.set("prism2_rotate", 0)
        self.set("rotating_gobo", 0)
        self.set("gobo_rotation", 0)
        self.set("focus", 0)
        self.set("zoom", 128)
        self.set("frost", 0)
        self.set("beam_diffraction", 0)


class ChauvetRogueHybridRH1_25Ch(ChauvetRogueHybridRH1_20Ch):
    """25-channel DMX mode — set fixture menu to ``DMX 25CH``.

    Adds Fine Dimmer / Fine Focus / Fine Zoom / Movement Macros to the 20CH
    layout. Inherits the startup blackout-on-wheel-move sequence.
    """

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
        # Bypass the 20CH __init__ and call ChauvetMoverBase directly with the
        # 25CH layout. Then re-park the optional channels for the wider layout.
        ChauvetMoverBase.__init__(
            self,
            patch,
            "chauvet rogue rh1 hybrid 25ch",
            25,
            DMX_LAYOUT_25,
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
            strobe_shutter_upper=SLOW_STROBE_SHUTTER_UPPER_DMX,
            disable_fine=False,
            universe=universe,
        )
        self.set("control", 0)
        self.set("movement_macros", 0)
        self.set("movement_macro_speed", 0)
        self.set("prism1", 0)
        self.set("prism1_rotate", 0)
        self.set("prism2", 0)
        self.set("prism2_rotate", 0)
        self.set("rotating_gobo", 0)
        self.set("gobo_rotation", 0)
        self.set("focus", 0)
        self.set("zoom", 128)
        self.set("frost", 0)
        self.set("beam_diffraction", 0)
        self.set("dimmer_fine", 0)
        self.set("focus_fine", 0)
        self.set("zoom_fine", 0)
