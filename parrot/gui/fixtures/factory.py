from parrot.fixtures.led_par import LedPar
from parrot.fixtures.moving_head import MovingHead
from parrot.fixtures.motionstrip import Motionstrip
from parrot.fixtures.laser import Laser
from parrot.fixtures.base import FixtureBase
from parrot.gui.fixtures.base import FixtureGuiRenderer
from parrot.gui.fixtures.bulb import BulbRenderer
from parrot.gui.fixtures.laser import LaserRenderer
from parrot.gui.fixtures.motionstrip import MotionstripRenderer
from parrot.gui.fixtures.moving_head import MovingHeadRenderer
from parrot.fixtures.chauvet.rotosphere import ChauvetRotosphere_28Ch
from parrot.gui.fixtures.rotosphere import RotosphereRenderer


def renderer_for_fixture(fixture: FixtureBase) -> FixtureGuiRenderer:
    if isinstance(fixture, LedPar):
        return BulbRenderer(fixture)
    elif isinstance(fixture, Laser):
        return LaserRenderer(fixture)
    elif isinstance(fixture, Motionstrip):
        return MotionstripRenderer(fixture)
    elif isinstance(fixture, MovingHead):
        return MovingHeadRenderer(fixture)
    elif isinstance(fixture, ChauvetRotosphere_28Ch):
        return RotosphereRenderer(fixture)
    else:
        raise NotImplementedError(f"Renderer for {fixture} not implemented")
