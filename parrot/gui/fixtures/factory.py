from parrot.fixtures.led_par import Par, ParRGB
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
from parrot.fixtures.chauvet.par import ChauvetParRGBWU
from parrot.fixtures.chauvet.derby import ChauvetDerby


def renderer_for_fixture(fixture: FixtureBase) -> FixtureGuiRenderer:
    if isinstance(fixture, Par):
        return BulbRenderer(fixture)
    elif isinstance(fixture, Laser):
        return LaserRenderer(fixture)
    elif isinstance(fixture, Motionstrip):
        return MotionstripRenderer(fixture)
    elif isinstance(fixture, MovingHead):
        return MovingHeadRenderer(fixture)
    elif isinstance(fixture, ChauvetRotosphere_28Ch):
        return RotosphereRenderer(fixture)
    elif isinstance(fixture, ChauvetDerby):
        return BulbRenderer(fixture)
    else:
        raise NotImplementedError(f"Renderer for {fixture} not implemented")
