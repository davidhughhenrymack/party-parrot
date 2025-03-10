from parrot.fixtures.led_par import ParRGB, ParRGBAWU
from parrot.fixtures.motionstrip import Motionstrip38
from parrot.fixtures.base import FixtureBase, FixtureGroup, ManualGroup

from parrot.fixtures.chauvet.intimidator120 import ChauvetSpot120_12Ch
from parrot.fixtures.chauvet.intimidator160 import ChauvetSpot160_12Ch
from parrot.fixtures.chauvet.gigbar import ChauvetGigBarMoveILS
from parrot.fixtures.chauvet.slimpar_pro_q import ChauvetSlimParProQ_5Ch
from parrot.fixtures.chauvet.slimpar_pro_h import ChauvetSlimParProH_7Ch
from parrot.fixtures.chauvet.colorband_pix import ChauvetColorBandPiX_36Ch
import enum

from parrot.fixtures.oultia.laser import TwoBeamLaser
from parrot.fixtures.uking.laser import FiveBeamLaser

venues = enum.Enum("Venues", ["dmack", "mtn_lotus", "truckee_theatre"])

# Create manual control fixtures for each venue
truckee_manual_fixtures = [
    FixtureBase(12, "Manual Bulb 12", 1),
    FixtureBase(15, "Manual Bulb 15", 1),
    FixtureBase(21, "Manual Bulb 15", 1),
    FixtureBase(24, "Manual Bulb 15", 1),
]

# Create manual control groups for each venue
manual_groups = {
    venues.truckee_theatre: ManualGroup(
        truckee_manual_fixtures, "Truckee Manual Control"
    ),
    venues.dmack: None,
    venues.mtn_lotus: None,
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
        # GigbarMove ILS 50 channel
        *ChauvetGigBarMoveILS(100),
        TwoBeamLaser(150),
        ChauvetSpot120_12Ch(160),
        ChauvetSpot160_12Ch(172),
    ],
    venues.truckee_theatre: [
        # Manual control fixtures
        manual_groups[venues.truckee_theatre],
        # 6 COLORband PiX fixtures (36 channels each)
        FixtureGroup(
            [ChauvetColorBandPiX_36Ch(i) for i in range(194, 375, 36)],
            "ColorBand wash",
        ),
        # 6 SlimPAR Pro H fixtures (7 channels each)
        FixtureGroup(
            [ChauvetSlimParProH_7Ch(i) for i in range(70, 106, 7)]
            + [ChauvetSlimParProH_7Ch(i) for i in range(112, 148, 7)],
            "Stage overhead",
        ),
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
            [ChauvetSpot160_12Ch(i) for i in range(400, 400 + 12 * 6, 12)],
            "Moving heads back",
        ),
        FixtureGroup(
            [FiveBeamLaser(i) for i in range(480, 480 + 14 * 2, 14)],
            "Lasers back",
        ),
    ],
}


def get_manual_group(venue):
    """Get the manual control group for a venue."""
    return manual_groups.get(venue)
