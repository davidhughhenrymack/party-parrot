#!/usr/bin/env python3

from beartype import beartype
from typing import Optional, Any

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
def create_renderer(
    fixture: FixtureBase, room_renderer: Optional[Any] = None
) -> FixtureRenderer:
    """
    Factory function to create the appropriate 3D renderer for a fixture.
    All renderers now render in 3D space.

    Args:
        fixture: The fixture to create a renderer for
        room_renderer: Room3DRenderer instance for 3D rendering
    """
    if isinstance(fixture, MovingHead):
        return MovingHeadRenderer(fixture, room_renderer)
    elif isinstance(fixture, Laser):
        return LaserRenderer(fixture, room_renderer)
    elif isinstance(fixture, Motionstrip):
        return MotionstripRenderer(fixture, room_renderer)
    else:
        # Default to bulb renderer for all other fixtures
        return BulbRenderer(fixture, room_renderer)
