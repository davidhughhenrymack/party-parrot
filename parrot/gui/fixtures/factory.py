from parrot.fixtures.led_par import Par, ParRGB
from parrot.fixtures.moving_head import MovingHead
from parrot.fixtures.motionstrip import Motionstrip
from parrot.fixtures.laser import Laser
from parrot.fixtures.base import FixtureBase, ManualGroup
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
    """Create a renderer for a fixture.

    Note: This function no longer handles FixtureGroups as they are unpacked by the GUI.
    ManualGroup is still handled directly for backward compatibility.
    """
    if isinstance(fixture, ManualGroup):
        # For backward compatibility, still handle ManualGroup directly
        renderer = FixtureGroupRenderer(fixture)
        renderer.setup_renderers(lambda f: BulbRenderer(f))
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
    # Default case for simple FixtureBase objects (like manual bulbs)
    elif isinstance(fixture, FixtureBase):
        return BulbRenderer(fixture)
    else:
        raise NotImplementedError(f"Renderer for {fixture} not implemented")
