from parrot.fixtures.led_par import ParRGB, ParRGBAWU
from parrot.fixtures.motionstrip import Motionstrip38
from parrot.fixtures.base import FixtureBase, FixtureGroup, ManualGroup

from parrot.fixtures.chauvet.intimidator110 import ChauvetSpot110_12Ch
from parrot.fixtures.chauvet.rogue_beam_r2 import ChauvetRogueBeamR2
from parrot.fixtures.chauvet.intimidator160 import ChauvetSpot160_12Ch
from parrot.fixtures.chauvet.gigbar import ChauvetGigBarMoveILS
from parrot.fixtures.chauvet.slimpar_pro_q import ChauvetSlimParProQ_5Ch
import enum

from parrot.fixtures.oultia.laser import TwoBeamLaser
from parrot.fixtures.uking.laser import FiveBeamLaser
from parrot.utils.dmx_utils import Universe

venues = enum.Enum(
    "Venues", ["dmack", "mtn_lotus", "truckee_theatre", "crux_test", "big"]
)

# Create manual control fixtures for each venue
truckee_manual_fixtures = [
    *[FixtureBase(i, f"Manual Bulb {i}", 1) for i in range(1, 9)],
]

# Create manual control groups for each venue
manual_groups = {
    venues.truckee_theatre: ManualGroup(
        truckee_manual_fixtures, "Truckee Manual Control"
    ),
    venues.dmack: None,
    venues.mtn_lotus: ManualGroup(
        [
            FixtureBase(1, "SR spot", 1, universe=Universe.art1),
            FixtureBase(2, "SL spot", 1, universe=Universe.art1),
        ]
    ),
    venues.crux_test: None,
    venues.big: None,
}

venue_patches = {
    venues.dmack: [
        ChauvetSpot160_12Ch(
            patch=1,
        ),
        ChauvetSpot110_12Ch(
            patch=140,
        ),
        *[ParRGB(i) for i in range(12, 48, 7)],
        Motionstrip38(154, 0, 256, invert_pan=True),
        Motionstrip38(59, 0, 256, invert_pan=True),
        FiveBeamLaser(100),
        TwoBeamLaser(120),
        # ChauvetRotosphere_28Ch(164),
    ],
    venues.mtn_lotus: [
        # Address 1 and 2 are the front spots.
        *[
            ParRGBAWU(i, universe=Universe.art1) for i in range(10, 90, 10)
        ],  # 10-20-30-40 is back line of pars. 50-60-70-80 is front line of pars.
        # Stage left column
        Motionstrip38(90, 0, 256),  # Stage left column
        ParRGB(195),  # Stage left top par
        ParRGB(205),  # Stage left bottom par
        ChauvetSpot160_12Ch(182),  # Stage left spot
        # --------
        TwoBeamLaser(220),
        # --------
        # Stage right column
        Motionstrip38(130, 0, 256),  # Stage right column
        ParRGB(230),  # Stage right top par
        ParRGB(238),  # Stage right bottom par
        ChauvetSpot110_12Ch(170),  # Stage right spot
        # --------
    ],
    venues.truckee_theatre: [
        # 6 COLORband PiX fixtures (36 channels each)
        # FixtureGroup(
        #     [ChauvetColorBandPiX_36Ch(i) for i in range(194, 375, 36)],
        #     "ColorBand wash",
        # ),
        # 6 SlimPAR Pro H fixtures (7 channels each)
        # FixtureGroup(
        #     # [ChauvetSlimParProH_7Ch(i) for i in range(70, 106, 7)],
        #     [ChauvetSlimParProH_7Ch(i) for i in range(112, 148, 7)],
        #     "Stage overhead",
        # ),
        # 6 more SlimPAR Pro H fixtures (7 channels each)
        # 4 SlimPAR Pro Q fixtures (5 channels each)
        FixtureGroup(
            [ChauvetSlimParProQ_5Ch(i) for i in range(154, 170, 5)]
            + [ChauvetSlimParProQ_5Ch(i) for i in range(174, 190, 5)],
            "Sidelights",
        ),
        # 8 more SlimPAR Pro Q fixtures (5 channels each)
        FixtureGroup(
            [ChauvetSlimParProQ_5Ch(i) for i in range(30, 66, 5)],
            "Front led wash",
        ),
        FixtureGroup(
            [
                *[ChauvetRogueBeamR2(i) for i in range(191, 191 + 15 * 6, 15)],
                *[ParRGB(i) for i in range(67, 67 + 6 * 7, 7)],
            ],
            "Moving heads crescent",
        ),
        FixtureGroup(
            [
                ChauvetSpot160_12Ch(
                    1,
                ),
                ChauvetSpot110_12Ch(
                    13,
                ),
                ParRGB(450),
                ParRGB(460),
            ],
            "Mirror ball",
        ),
        FixtureGroup(
            [
                Motionstrip38(300, pan_lower=128, pan_upper=256),
                Motionstrip38(300 + 38, pan_lower=128, pan_upper=256),
            ],
            "Motion strip (doubled)",
        ),
        FixtureGroup([ParRGB(i) for i in range(400, 400 + 4 * 7, 7)], "Spare Pars"),
    ],
    venues.crux_test: [
        FixtureGroup(
            [ChauvetRogueBeamR2(1), ChauvetRogueBeamR2(16)],
            "Rogue Beams",
        ),
    ],
    venues.big: [
        # 8 moving lights along top of video wall (back wall, high)
        *[
            ChauvetSpot160_12Ch(i) for i in range(10, 90, 10)
        ],  # 10, 20, 30, 40, 50, 60, 70, 80
        # 8 moving lights along base of video wall (audience side, low)
        *[
            ChauvetSpot160_12Ch(i) for i in range(100, 180, 10)
        ],  # 100, 110, 120, 130, 140, 150, 160, 170
        # 4x4 grid of moving lights in ceiling (upside down, pointing down)
        *[
            ChauvetSpot160_12Ch(i) for i in range(200, 400, 12)
        ],  # 200, 212, 224, 236, 248, 260, 272, 284, 296, 308, 320, 332, 344, 356, 368, 380
    ],
}


def get_manual_group(venue):
    """Get the manual control group for a venue."""
    return manual_groups.get(venue)


def has_manual_dimmer(venue):
    """Check if a venue has manual dimmers."""
    return manual_groups.get(venue) is not None
