#!/usr/bin/env python3

from beartype import beartype

from parrot.fixtures.base import FixtureBase
from parrot.fixtures.moving_head import MovingHead
from parrot.fixtures.laser import Laser
from parrot.fixtures.motionstrip import Motionstrip
from parrot.vj.renderers.base import FixtureRenderer
from parrot.vj.renderers.bulb import BulbRenderer
from parrot.vj.renderers.moving_head import MovingHeadRenderer
from parrot.vj.renderers.laser import LaserRenderer
from parrot.vj.renderers.motionstrip import MotionstripRenderer


@beartype
def create_renderer(fixture: FixtureBase) -> FixtureRenderer:
    """
    Factory function to create the appropriate renderer for a fixture.
    Similar to renderer_for_fixture in the legacy GUI.
    """
    if isinstance(fixture, MovingHead):
        return MovingHeadRenderer(fixture)
    elif isinstance(fixture, Laser):
        return LaserRenderer(fixture)
    elif isinstance(fixture, Motionstrip):
        return MotionstripRenderer(fixture)
    else:
        # Default to bulb renderer for all other fixtures
        return BulbRenderer(fixture)
