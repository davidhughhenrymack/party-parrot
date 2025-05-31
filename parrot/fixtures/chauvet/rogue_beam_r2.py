from parrot.utils.colour import Color
from parrot.fixtures.chauvet.mover_base import ChauvetMoverBase
from parrot.fixtures.base import GoboWheelEntry, ColorWheelEntry


# DMX layout:
dmx_layout = {
    "pan_coarse": 0,
    "pan_fine": 1,
    "tilt_coarse": 2,
    "tilt_fine": 3,
    "speed": 4,
    "dimmer": 5,
    "shutter": 6,
    "color_wheel": 7,
    "gobo_wheel": 8,
    "prism": 9,
    "prism_rotate": 10,
    "prism_zoom": 11,
    "focus": 12,
    "frost": 13,
    "control": 14,
}


color_wheel = [
    ColorWheelEntry(Color("white"), 2),  # Open (white)
    ColorWheelEntry(Color("red"), 6),  # Red (1)
    # ColorWheelEntry(Color("#FFD700"), 10),  # Deep yellow (2)
    ColorWheelEntry(Color("Turquoise"), 14),  # Turquoise (3)
    ColorWheelEntry(Color("green"), 18),  # Green (4)
    ColorWheelEntry(Color("lightgreen"), 22),  # Light green (5)
    ColorWheelEntry(Color("Lightpink"), 26),  # Light purple (6)
    ColorWheelEntry(Color("pink"), 30),  # Pink (7)
    # ColorWheelEntry(Color("#FFFF00"), 34),  # Light yellow (8)
    ColorWheelEntry(Color("magenta"), 38),  # Magenta (9)
    ColorWheelEntry(Color("blue"), 42),  # Blue (10)
    # ColorWheelEntry(Color("#FFA500"), 46),  # CTO 3200K (11)
    # ColorWheelEntry(Color("#FFA500"), 50),  # CTO 5600K (12)
    # ColorWheelEntry(Color("#FFA500"), 54),  # CTO 6500K (13)
    ColorWheelEntry(Color("BlueViolet"), 58),  # UV (14)
    # Split colors: 61-127
    # Clockwise scroll (fast → slow): 128-189
    # Stop: 190-193
    # Counter-clockwise scroll (slow → fast): 194-255
]

gobo_wheel = [
    GoboWheelEntry("open", 0),  # Open
    GoboWheelEntry("gobo1", 4),  # Gobo 1
    GoboWheelEntry("gobo2", 7),  # Gobo 2
    GoboWheelEntry("gobo3", 10),  # Gobo 3
    GoboWheelEntry("gobo4", 13),  # Gobo 4
    GoboWheelEntry("gobo5", 16),  # Gobo 5
    GoboWheelEntry("gobo6", 19),  # Gobo 6
    GoboWheelEntry("gobo7", 22),  # Gobo 7
    GoboWheelEntry("gobo8", 25),  # Gobo 8
    GoboWheelEntry("gobo9", 28),  # Gobo 9
    GoboWheelEntry("gobo10", 31),  # Gobo 10
    GoboWheelEntry("gobo11", 34),  # Gobo 11
    GoboWheelEntry("gobo12", 37),  # Gobo 12
    GoboWheelEntry("gobo13", 40),  # Gobo 13
    GoboWheelEntry("gobo14", 43),  # Gobo 14
    GoboWheelEntry("gobo15", 46),  # Gobo 15
    GoboWheelEntry("gobo16", 49),  # Gobo 16
    GoboWheelEntry("gobo17", 52),  # Gobo 17
    GoboWheelEntry("open", 56),  # Open (again)
    # Gobo shake (1-17), slow → fast: 60-127
    # Clockwise scroll (fast → slow): 128-189
    # Stop: 190-193
    # Counter-clockwise scroll (slow → fast): 194-255
]


class ChauvetRogueBeamR2(ChauvetMoverBase):
    def __init__(
        self,
        patch,
        pan_lower=270,
        pan_upper=450,
        tilt_lower=0,
        tilt_upper=90,
        dimmer_upper=255,
    ):
        super().__init__(
            patch=patch,
            name="chauvet rogue beam r2",
            width=15,
            dmx_layout=dmx_layout,
            color_wheel=color_wheel,
            gobo_wheel=gobo_wheel,
            pan_lower=pan_lower,
            pan_upper=pan_upper,
            tilt_lower=tilt_lower,
            tilt_upper=tilt_upper,
            dimmer_upper=dimmer_upper,
            shutter_open=255,
            speed_value=0,
            strobe_shutter_lower=16,
            strobe_shutter_upper=131,
            disable_fine=False,
        )

        self.disable_blackout_on_all_fn = 225
        self.set("control", self.disable_blackout_on_all_fn)
