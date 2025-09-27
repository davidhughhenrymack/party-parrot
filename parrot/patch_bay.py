from parrot.fixtures.led_par import ParRGB, ParRGBAWU
from parrot.fixtures.motionstrip import Motionstrip38
from parrot.fixtures.base import FixtureBase, FixtureGroup, ManualGroup

from parrot.fixtures.chauvet.intimidator120 import ChauvetSpot120_12Ch
from parrot.fixtures.chauvet.rogue_beam_r2 import ChauvetRogueBeamR2
from parrot.fixtures.chauvet.intimidator160 import ChauvetSpot160_12Ch
from parrot.fixtures.chauvet.gigbar import ChauvetGigBarMoveILS
from parrot.fixtures.chauvet.slimpar_pro_q import ChauvetSlimParProQ_5Ch
import enum

from parrot.fixtures.oultia.laser import TwoBeamLaser
from parrot.fixtures.uking.laser import FiveBeamLaser

venues = enum.Enum("Venues", ["dmack", "mtn_lotus", "truckee_theatre", "crux_test"])

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
    venues.mtn_lotus: None,
    venues.crux_test: None,
}

# Track which venues have manual dimmers
has_manual_dimmers = {
    venues.truckee_theatre: True,
    venues.dmack: False,
    venues.mtn_lotus: False,
    venues.crux_test: False,
}

venue_patches = {
    venues.dmack: [
        ChauvetSpot160_12Ch(
            patch=1,
        ),
        ChauvetSpot120_12Ch(
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
        *[ParRGBAWU(i) for i in range(10, 90, 10)],
        Motionstrip38(80, 0, 256),
        Motionstrip38(108, 0, 256),
        ParRGB(192),
        ParRGB(199),
        # GigbarMove ILS 50 channel
        # *ChauvetGigBarMoveILS(100),
        TwoBeamLaser(150),
        ChauvetSpot120_12Ch(160),
        ChauvetSpot160_12Ch(172),
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
                ChauvetSpot120_12Ch(
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
}


def get_manual_group(venue):
    """Get the manual control group for a venue."""
    return manual_groups.get(venue)


def has_manual_dimmer(venue):
    """Check if a venue has manual dimmers."""
    return has_manual_dimmers.get(venue, False)
