from parrot.fixtures.led_par import Par, ParRGB
from parrot.fixtures.moving_head import MovingHead
from parrot.fixtures.motionstrip import Motionstrip
from parrot.fixtures.laser import Laser
from parrot.fixtures.base import FixtureBase, FixtureGroup
from parrot.gui.fixtures.base import FixtureGuiRenderer
from parrot.gui.fixtures.bulb import (
    BulbRenderer,
    RectBulbRenderer,
    RoundedRectBulbRenderer,
)
from parrot.gui.fixtures.laser import LaserRenderer
from parrot.gui.fixtures.motionstrip import MotionstripRenderer
from parrot.gui.fixtures.moving_head import MovingHeadRenderer
from parrot.fixtures.chauvet.rotosphere import ChauvetRotosphere_28Ch
from parrot.gui.fixtures.rotosphere import RotosphereRenderer
from parrot.fixtures.chauvet.par import ChauvetParRGBAWU
from parrot.fixtures.chauvet.derby import ChauvetDerby
from parrot.fixtures.chauvet.colorband_pix import ChauvetColorBandPiX_36Ch
from parrot.gui.fixtures.colorband import ColorBandRenderer
from parrot.fixtures.chauvet.slimpar_pro_q import ChauvetSlimParProQ_5Ch
from parrot.fixtures.chauvet.slimpar_pro_h import ChauvetSlimParProH_7Ch
from parrot.gui.fixtures.group import FixtureGroupRenderer


def renderer_for_fixture(fixture: FixtureBase) -> FixtureGuiRenderer:
    if isinstance(fixture, FixtureGroup):
        renderer = FixtureGroupRenderer(fixture)
        renderer.setup_renderers(renderer_for_fixture)
        return renderer
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
    elif isinstance(fixture, ChauvetColorBandPiX_36Ch):
        return ColorBandRenderer(fixture)
    elif isinstance(fixture, ChauvetSlimParProQ_5Ch):
        return RectBulbRenderer(fixture)
    elif isinstance(fixture, ChauvetSlimParProH_7Ch):
        return RoundedRectBulbRenderer(fixture)
    elif isinstance(fixture, Par):
        return BulbRenderer(fixture)
    else:
        raise NotImplementedError(f"Renderer for {fixture} not implemented")
