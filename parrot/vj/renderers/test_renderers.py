#!/usr/bin/env python3

import pytest
import moderngl as mgl

from parrot.fixtures.led_par import ParRGB
from parrot.fixtures.chauvet.intimidator160 import ChauvetSpot160_12Ch
from parrot.fixtures.oultia.laser import TwoBeamLaser
from parrot.fixtures.motionstrip import Motionstrip38
from parrot.vj.renderers.factory import create_renderer
from parrot.vj.renderers.bulb import BulbRenderer
from parrot.vj.renderers.moving_head import MovingHeadRenderer
from parrot.vj.renderers.laser import LaserRenderer
from parrot.vj.renderers.motionstrip import MotionstripRenderer
from parrot.utils.colour import Color
from parrot.director.frame import Frame, FrameSignal


def test_factory_creates_bulb_renderer():
    """Test that factory creates BulbRenderer for PAR fixtures"""
    fixture = ParRGB(1)
    renderer = create_renderer(fixture)
    assert isinstance(renderer, BulbRenderer)


def test_factory_creates_moving_head_renderer():
    """Test that factory creates MovingHeadRenderer for MovingHead fixtures"""
    fixture = ChauvetSpot160_12Ch(1)
    renderer = create_renderer(fixture)
    assert isinstance(renderer, MovingHeadRenderer)


def test_factory_creates_laser_renderer():
    """Test that factory creates LaserRenderer for Laser fixtures"""
    fixture = TwoBeamLaser(100)
    renderer = create_renderer(fixture)
    assert isinstance(renderer, LaserRenderer)


def test_factory_creates_motionstrip_renderer():
    """Test that factory creates MotionstripRenderer for Motionstrip fixtures"""
    fixture = Motionstrip38(80, 0, 256)
    renderer = create_renderer(fixture)
    assert isinstance(renderer, MotionstripRenderer)


def test_bulb_renderer_size():
    """Test that BulbRenderer returns correct size"""
    fixture = ParRGB(1)
    renderer = BulbRenderer(fixture)
    width, height = renderer.size
    assert width == 30.0
    assert height == 30.0


def test_moving_head_renderer_size():
    """Test that MovingHeadRenderer returns correct size"""
    fixture = ChauvetSpot160_12Ch(1)
    renderer = MovingHeadRenderer(fixture)
    width, height = renderer.size
    assert width == 40.0
    assert height == 40.0


def test_renderer_set_position():
    """Test that renderer position can be set"""
    fixture = ParRGB(1)
    renderer = BulbRenderer(fixture)
    renderer.set_position(100.0, 200.0)
    assert renderer.position == (100.0, 200.0)


def test_renderer_get_color():
    """Test that renderer can get fixture color"""
    fixture = ParRGB(1)
    fixture.set_color(Color("blue"))
    renderer = BulbRenderer(fixture)
    r, g, b = renderer.get_color()
    assert 0.0 <= r <= 1.0
    assert 0.0 <= g <= 1.0
    assert 0.0 <= b <= 1.0


def test_renderer_get_dimmer():
    """Test that renderer can get fixture dimmer"""
    fixture = ParRGB(1)
    fixture.set_dimmer(128)
    renderer = BulbRenderer(fixture)
    dimmer = renderer.get_dimmer()
    assert abs(dimmer - 128 / 255) < 0.01


def test_renderer_render_bulb():
    """Test that BulbRenderer.render() executes without error"""
    ctx = mgl.create_context(standalone=True)

    fixture = ParRGB(1)
    fixture.set_color(Color("red"))
    fixture.set_dimmer(255)

    renderer = BulbRenderer(fixture)
    renderer.set_position(100.0, 100.0)

    # Create a framebuffer to render to
    fbo = ctx.framebuffer(color_attachments=[ctx.texture((800, 600), 3)])
    fbo.use()
    ctx.clear(0.0, 0.0, 0.0)

    frame = Frame({signal: 0.0 for signal in FrameSignal})
    frame.time = 0.0

    # Should not crash
    renderer.render(ctx, (1200.0, 1200.0), frame)

    # Cleanup
    fbo.release()
    ctx.release()


def test_renderer_render_moving_head():
    """Test that MovingHeadRenderer.render() executes without error"""
    ctx = mgl.create_context(standalone=True)

    fixture = ChauvetSpot160_12Ch(1)
    fixture.set_color(Color("green"))
    fixture.set_dimmer(255)

    renderer = MovingHeadRenderer(fixture)
    renderer.set_position(200.0, 200.0)

    # Create a framebuffer to render to
    fbo = ctx.framebuffer(color_attachments=[ctx.texture((800, 600), 3)])
    fbo.use()
    ctx.clear(0.0, 0.0, 0.0)

    frame = Frame({signal: 0.0 for signal in FrameSignal})
    frame.time = 0.0

    # Should not crash
    renderer.render(ctx, (1200.0, 1200.0), frame)

    # Cleanup
    fbo.release()
    ctx.release()
