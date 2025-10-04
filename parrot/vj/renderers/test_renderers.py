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
    assert renderer.position == (100.0, 200.0, 3.0)  # Default z is 3.0

    # Test with explicit z
    renderer.set_position(150.0, 250.0, 5.0)
    assert renderer.position == (150.0, 250.0, 5.0)


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


def test_moving_head_beam_with_room_renderer():
    """Test that MovingHeadRenderer renders beam with room renderer"""
    from parrot.vj.renderers.room_3d import Room3DRenderer

    ctx = mgl.create_context(standalone=True)

    # Create room renderer
    room = Room3DRenderer(ctx, 800, 600)

    # Create moving head with color and dimmer
    fixture = ChauvetSpot160_12Ch(1)
    fixture.set_color(Color("blue"))
    fixture.set_dimmer(200)  # High dimmer to trigger beam
    fixture.set_pan(128)  # Pan to middle
    fixture.set_tilt(64)  # Tilt slightly down

    renderer = MovingHeadRenderer(fixture, room_renderer=room)
    renderer.set_position(250.0, 250.0)

    # Create a framebuffer to render to
    fbo = ctx.framebuffer(color_attachments=[ctx.texture((800, 600), 3)])
    fbo.use()
    ctx.clear(0.0, 0.0, 0.0)

    frame = Frame({signal: 0.0 for signal in FrameSignal})
    frame.time = 0.0

    # Should render beam without crashing
    renderer.render(ctx, (500.0, 500.0), frame)

    # Test with low dimmer (should not render beam)
    fixture.set_dimmer(10)  # Very low dimmer
    renderer.render(ctx, (500.0, 500.0), frame)

    # Cleanup
    room.cleanup()
    fbo.release()
    ctx.release()


def test_room_renderer_context_managers():
    """Test that local_position and local_rotation context managers work correctly"""
    from parrot.vj.renderers.room_3d import Room3DRenderer
    import numpy as np

    ctx = mgl.create_context(standalone=True)
    room = Room3DRenderer(ctx, 800, 600)

    # Test initial state
    assert len(room.position_stack) == 1
    assert len(room.rotation_stack) == 1
    assert room.position_stack[-1] == (0.0, 0.0, 0.0)

    # Test local_position context manager
    with room.local_position((1.0, 2.0, 3.0)):
        assert len(room.position_stack) == 2
        assert room.position_stack[-1] == (1.0, 2.0, 3.0)

        # Test nested position
        with room.local_position((4.0, 5.0, 6.0)):
            assert len(room.position_stack) == 3
            assert room.position_stack[-1] == (4.0, 5.0, 6.0)

        # Should pop back
        assert len(room.position_stack) == 2
        assert room.position_stack[-1] == (1.0, 2.0, 3.0)

    # Should pop back to initial
    assert len(room.position_stack) == 1
    assert room.position_stack[-1] == (0.0, 0.0, 0.0)

    # Test local_rotation context manager
    test_quat = np.array([0.0, 0.707, 0.0, 0.707], dtype=np.float32)
    with room.local_rotation(test_quat):
        assert len(room.rotation_stack) == 2
        assert np.allclose(room.rotation_stack[-1], test_quat)

    # Should pop back to identity
    assert len(room.rotation_stack) == 1

    # Cleanup
    room.cleanup()
    ctx.release()


def test_room_renderer_transform_stacks():
    """Test that transform stacks produce correct model matrices"""
    from parrot.vj.renderers.room_3d import Room3DRenderer
    import numpy as np

    ctx = mgl.create_context(standalone=True)
    room = Room3DRenderer(ctx, 800, 600)

    # Test identity model matrix
    model = room._get_current_model_matrix()
    assert np.allclose(model, np.eye(4, dtype=np.float32))

    # Test position transform
    with room.local_position((1.0, 2.0, 3.0)):
        model = room._get_current_model_matrix()
        # Check that translation is in the matrix
        assert abs(model[0, 3] - 1.0) < 0.01
        assert abs(model[1, 3] - 2.0) < 0.01
        assert abs(model[2, 3] - 3.0) < 0.01

    # Cleanup
    room.cleanup()
    ctx.release()


def test_room_renderer_circle():
    """Test that room renderer can render circles"""
    from parrot.vj.renderers.room_3d import Room3DRenderer

    ctx = mgl.create_context(standalone=True)
    room = Room3DRenderer(ctx, 800, 600)

    # Create a framebuffer to render to
    fbo = ctx.framebuffer(color_attachments=[ctx.texture((800, 600), 3)])
    fbo.use()
    ctx.clear(0.0, 0.0, 0.0)

    # Render a circle facing forward
    room.render_circle(
        position=(0.0, 1.0, 0.0),
        color=(1.0, 0.0, 0.0),
        radius=0.5,
        normal=(0.0, 0.0, 1.0),
        alpha=1.0,
    )

    # Should not crash
    # Cleanup
    fbo.release()
    room.cleanup()
    ctx.release()


def test_room_renderer_bulb_with_beam():
    """Test that room renderer can render bulbs with beams"""
    from parrot.vj.renderers.room_3d import Room3DRenderer

    ctx = mgl.create_context(standalone=True)
    room = Room3DRenderer(ctx, 800, 600)

    # Create a framebuffer to render to
    fbo = ctx.framebuffer(color_attachments=[ctx.texture((800, 600), 3)])
    fbo.use()
    ctx.clear(0.0, 0.0, 0.0)

    # Render a bulb with beam
    room.render_bulb_with_beam(
        position=(0.0, 1.0, 0.0),
        color=(0.0, 1.0, 0.0),
        bulb_radius=0.3,
        normal=(0.0, 0.0, 1.0),
        alpha=0.8,
        beam_length=5.0,
        beam_alpha=0.2,
    )

    # Should not crash
    # Cleanup
    fbo.release()
    room.cleanup()
    ctx.release()


def test_room_renderer_floor_optional():
    """Test that floor is optional and disabled by default"""
    from parrot.vj.renderers.room_3d import Room3DRenderer

    ctx = mgl.create_context(standalone=True)

    # Default: floor disabled
    room_no_floor = Room3DRenderer(ctx, 800, 600)
    assert room_no_floor.show_floor is False
    assert not hasattr(room_no_floor, "floor_vertices")

    # Explicitly enable floor
    room_with_floor = Room3DRenderer(ctx, 800, 600, show_floor=True)
    assert room_with_floor.show_floor is True
    assert hasattr(room_with_floor, "floor_vertices")
    assert len(room_with_floor.floor_vertices) > 0

    # Cleanup
    room_no_floor.cleanup()
    room_with_floor.cleanup()
    ctx.release()
