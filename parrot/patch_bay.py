from parrot.fixtures.led_par import ParRGB, ParRGBAWU, Par
from parrot.fixtures.motionstrip import Motionstrip38
from parrot.fixtures.base import FixtureBase, FixtureGroup, FixtureTag
from parrot.fixtures.moving_head import MovingHead
from typing import Dict, List, Optional

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

venue_patches = {
    venues.dmack: [
        ChauvetSpot160_12Ch(patch=1),
        ChauvetSpot120_12Ch(patch=140),
        *[ParRGB(i) for i in range(12, 48, 7)],
        Motionstrip38(154, 0, 256, invert_pan=True),
        Motionstrip38(59, 0, 256, invert_pan=True),
        FiveBeamLaser(100),
        TwoBeamLaser(120),
    ],
    venues.mtn_lotus: [
        *[ParRGBAWU(i) for i in range(10, 90, 10)],
        Motionstrip38(80, 0, 256),
        Motionstrip38(108, 0, 256),
        *ChauvetGigBarMoveILS(100),
        TwoBeamLaser(150),
        ChauvetSpot120_12Ch(160),
        ChauvetSpot160_12Ch(172),
    ],
    venues.truckee_theatre: [
        # Manual control fixtures
        FixtureGroup(
            [FixtureBase(i, f"Manual Bulb {i}", 1) for i in range(1, 9)],
            "Truckee Manual Control",
        ),
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
            [ChauvetSpot160_12Ch(i) for i in range(425, 425 + 12 * 6, 12)],
            "Moving heads back",
        ),
        FixtureGroup(
            [FiveBeamLaser(i) for i in range(480, 480 + 14 * 2, 14)],
            "Lasers back",
        ),
    ],
}


def get_fixture_types() -> List[type[FixtureBase]]:
    """Get all fixture types used across all venues."""
    fixture_types = set()
    for venue_fixtures in venue_patches.values():
        for fixture in venue_fixtures:
            if isinstance(fixture, FixtureGroup):
                for sub_fixture in fixture:
                    fixture_types.add(type(sub_fixture))
            else:
                fixture_types.add(type(fixture))
    return list(fixture_types)


def get_fixture_addresses(fixture_type: type[FixtureBase]) -> List[int]:
    """Get all addresses for a given fixture type across all venues."""
    addresses = set()
    for venue_fixtures in venue_patches.values():
        for fixture in venue_fixtures:
            if isinstance(fixture, FixtureGroup):
                for sub_fixture in fixture:
                    if isinstance(sub_fixture, fixture_type):
                        addresses.add(sub_fixture.address)
            elif isinstance(fixture, fixture_type):
                addresses.add(fixture.address)
    return sorted(list(addresses))


def has_manual_dimmer(venue: venues) -> bool:
    """Check if a venue has manual dimmer fixtures."""
    for fixture in venue_patches[venue]:
        if isinstance(fixture, FixtureGroup):
            for sub_fixture in fixture:
                if isinstance(sub_fixture, FixtureBase) and sub_fixture.width == 1:
                    return True
        elif isinstance(fixture, FixtureBase) and fixture.width == 1:
            return True
    return False


def get_manual_group(venue: venues) -> Optional[FixtureGroup]:
    """Get the manual dimmer fixture group for a venue."""
    for fixture in venue_patches[venue]:
        if isinstance(fixture, FixtureGroup):
            # Check if all fixtures in the group are manual dimmers
            if all(isinstance(f, FixtureBase) and f.width == 1 for f in fixture):
                return fixture
    return None
