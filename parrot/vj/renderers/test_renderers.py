#!/usr/bin/env python3

import pytest
import moderngl as mgl

from parrot.fixtures.led_par import ParRGB
from parrot.fixtures.chauvet.intimidator160 import ChauvetSpot160_12Ch
from parrot.fixtures.oultia.laser import TwoBeamLaser
from parrot.fixtures.motionstrip import Motionstrip38
from parrot.fixtures.mirrorball import Mirrorball
from parrot.vj.renderers.factory import create_renderer
from parrot.vj.renderers.bulb import BulbRenderer
from parrot.vj.renderers.mirrorball import MirrorballRenderer
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


def test_factory_creates_mirrorball_renderer():
    fixture = Mirrorball(1)
    renderer = create_renderer(fixture)
    assert isinstance(renderer, MirrorballRenderer)


def test_mirrorball_renderer_with_room():
    from parrot.vj.renderers.room_3d import Room3DRenderer

    ctx = mgl.create_context(standalone=True)
    room = Room3DRenderer(ctx, 800, 600)
    fixture = Mirrorball(1)
    fixture.set_color(Color("white"))
    fixture.set_dimmer(255)
    renderer = MirrorballRenderer(fixture, room_renderer=room)
    renderer.set_position(100.0, 100.0)
    fbo = ctx.framebuffer(color_attachments=[ctx.texture((800, 600), 3)])
    fbo.use()
    ctx.clear(0.0, 0.0, 0.0)
    frame = Frame({signal: 0.0 for signal in FrameSignal})
    frame.time = 0.0
    renderer.render_opaque(ctx, (500.0, 500.0), frame)
    renderer.render_emissive(ctx, (500.0, 500.0), frame)
    fbo.release()
    ctx.release()


def test_emission_circle_blends_additively_over_beams():
    """Emission circles must NOT darken pixels already lit by beams.

    Regression: ``render_emission_circle`` used to flip blend mode to
    ``SRC_ALPHA, ONE_MINUS_SRC_ALPHA`` (or leave blending off entirely for
    opaque bulbs), which, in the emissive pass, let a later bulb draw
    overwrite pixels that earlier beams had additively lit. Visually this
    looked like e.g. a mirrorball beam "darkening" a moving-head beam
    wherever it crossed the fixture's bulb disc.

    We simulate pass 2 (`SRC_ALPHA, ONE` blending, no depth test) by
    pre-filling the emissive framebuffer with a known bright color, then
    drawing a colored emission circle over it and asserting pixels inside
    the circle are strictly ≥ the pre-fill on every channel (additive can
    only brighten).
    """
    from parrot.vj.renderers.room_3d import Room3DRenderer

    ctx = mgl.create_context(standalone=True)
    width, height = 128, 128
    room = Room3DRenderer(ctx, width, height)

    tex = ctx.texture((width, height), 3)
    fbo = ctx.framebuffer(color_attachments=[tex])
    fbo.use()
    # Pre-fill with a dim non-zero color - this represents accumulated beam
    # contribution from an earlier renderer in the emissive pass.
    prefill = (0.4, 0.1, 0.05)
    ctx.clear(*prefill)

    # Draw an emission circle centered on the framebuffer. This call must
    # leave every pixel it touches no dimmer than `prefill` on any channel.
    room.render_emission_circle(
        position=(0.0, 0.0, 0.0),
        color=(0.2, 0.3, 0.4),
        radius=0.3,
        normal=(0.0, 0.0, 1.0),
        alpha=0.6,
    )

    import numpy as np

    raw = np.frombuffer(tex.read(), dtype=np.uint8).reshape((height, width, 3))
    prefill_u8 = np.array([int(round(c * 255)) for c in prefill], dtype=np.int16)
    diff = raw.astype(np.int16) - prefill_u8  # per-pixel per-channel delta
    # Any pixel where all channels exactly match pre-fill is outside the
    # circle; pixels inside the circle must be >= pre-fill on every channel
    # (slack of 1 for rounding).
    assert diff.min() >= -1, (
        f"emission circle darkened the framebuffer: min delta={diff.min()} "
        "(expected >= -1 since additive blending can't reduce any channel)"
    )
    # Sanity check: at least some pixels actually got brighter — i.e. the
    # circle was drawn, the test isn't trivially passing on an empty draw.
    assert diff.max() > 5, "emission circle draw didn't noticeably change any pixel"

    fbo.release()
    tex.release()
    ctx.release()


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


def test_moving_head_rotation_is_pan_then_tilt():
    """Regression: the yoke rotation must be ``pan ∘ tilt`` (pan outer, tilt
    inner), matching real moving-head mechanics — the yoke pans around world-Y,
    then the head tilts around the *panned* yoke X. A previous implementation
    used ``tilt * pan`` which made the beam and the body diverge as soon as
    both pan and tilt were non-zero.

    We verify this by composing the expected ``pan_quat * tilt_quat`` from the
    same renderer-side pan/tilt radians and comparing to
    ``_moving_body_rotation()``.
    """
    import math
    import numpy as np
    from parrot.vj.renderers.base import (
        quaternion_from_axis_angle,
        quaternion_multiply,
        quaternion_rotate_vector,
    )

    fixture = ChauvetSpot160_12Ch(1)
    fixture.set_pan(64)
    fixture.set_tilt(192)
    renderer = MovingHeadRenderer(fixture)

    pan_rad, tilt_rad = renderer._pan_tilt_radians_for_render()
    y_axis = np.array([0.0, 1.0, 0.0], dtype=np.float32)
    x_axis = np.array([1.0, 0.0, 0.0], dtype=np.float32)
    pan_quat = quaternion_from_axis_angle(y_axis, pan_rad)
    tilt_quat = quaternion_from_axis_angle(x_axis, tilt_rad)

    expected_pan_then_tilt = quaternion_multiply(pan_quat, tilt_quat)
    wrong_tilt_then_pan = quaternion_multiply(tilt_quat, pan_quat)

    actual = renderer._moving_body_rotation()

    assert np.allclose(actual, expected_pan_then_tilt, atol=1e-5), (
        f"Expected pan∘tilt {expected_pan_then_tilt}, got {actual}"
    )
    # And sanity-check it is NOT the reversed order (which would regress the
    # body/beam-diverge bug).
    assert not np.allclose(actual, wrong_tilt_then_pan, atol=1e-3)

    # Beam direction sanity: body-local +Z rotated by pan∘tilt should match
    # rotating +Z first by tilt (around X), then by pan (around Y).
    local_forward = np.array([0.0, 0.0, 1.0], dtype=np.float32)
    via_composed = quaternion_rotate_vector(actual, local_forward)
    tilt_first = quaternion_rotate_vector(tilt_quat, local_forward)
    pan_last = quaternion_rotate_vector(pan_quat, tilt_first)
    assert np.allclose(via_composed, pan_last, atol=1e-5)


def test_moving_head_at_dmx_127_with_full_tilt_points_up():
    """End-to-end: a fixture with full mechanical tilt range, set to DMX tilt=127,
    should render with the beam pointing straight up (world +Y).

    Covers the ChauvetMoverBase.set_tilt → MovingHead.tilt_angle → renderer
    pipeline including the +π pan offset. Pan is left at DMX=0 (logical pan=0).
    """
    import numpy as np
    from parrot.vj.renderers.base import quaternion_rotate_vector

    # Full mechanical sweep: tilt_lower=0° → DMX 0, tilt_upper=270° → DMX 255.
    fixture = ChauvetSpot160_12Ch(1, tilt_lower=0.0, tilt_upper=270.0)
    fixture.set_pan(0)
    fixture.set_tilt(127)
    renderer = MovingHeadRenderer(fixture)

    local_forward = np.array([0.0, 0.0, 1.0], dtype=np.float32)
    world_beam = quaternion_rotate_vector(
        renderer._moving_body_rotation(), local_forward
    )
    # Beam should be (approximately) world +Y with small tolerance since DMX 127
    # is very near (but not exactly) logical tilt 135°.
    assert np.isclose(world_beam[0], 0.0, atol=5e-2)
    assert np.isclose(world_beam[1], 1.0, atol=5e-2), (
        f"expected beam up (+Y), got {world_beam}"
    )
    assert np.isclose(world_beam[2], 0.0, atol=5e-2)


def test_moving_head_full_tilt_endpoints_symmetric_from_up():
    """DMX 0 and DMX 255 (full range) should place the beam ±135° away from up."""
    import math
    import numpy as np
    from parrot.vj.renderers.base import quaternion_rotate_vector

    fixture = ChauvetSpot160_12Ch(1, tilt_lower=0.0, tilt_upper=270.0)
    fixture.set_pan(0)
    local_forward = np.array([0.0, 0.0, 1.0], dtype=np.float32)
    up = np.array([0.0, 1.0, 0.0], dtype=np.float32)

    fixture.set_tilt(0)
    beam_low = quaternion_rotate_vector(
        MovingHeadRenderer(fixture)._moving_body_rotation(), local_forward
    )
    fixture.set_tilt(255)
    beam_high = quaternion_rotate_vector(
        MovingHeadRenderer(fixture)._moving_body_rotation(), local_forward
    )

    angle_low = math.degrees(math.acos(float(np.dot(beam_low, up))))
    angle_high = math.degrees(math.acos(float(np.dot(beam_high, up))))
    assert angle_low == pytest.approx(135.0, abs=1.5)
    assert angle_high == pytest.approx(135.0, abs=1.5)


def test_moving_head_floor_vs_truss_base_head_stacking():
    """Regression: on a floor mover the head sits ABOVE the base, and on a
    truss-flipped (rotation_x=π) mover the head hangs BELOW the base.

    The old renderer placed the head at an offset inside the rotated body
    frame, so the rest -π/2 tilt flung the head to y≈−0.18 (below the floor)
    for floor movers and y≈+9.55 (above the ceiling pivot) for truss movers —
    visually making the base appear upside-down vs. the web preview. The new
    renderer pivots pan/tilt around the yoke center, matching Parrot Cloud's
    ``headPivotGroup``.
    """
    import math
    import numpy as np
    from parrot.vj.renderers.moving_head import (
        _moving_head_dimensions,
        _head_pivot_world,
    )
    from parrot.vj.renderers.base import quaternion_rotate_vector
    from parrot.vj.venue_axis import venue_rotation_to_desktop_quaternion

    fixture = ChauvetSpot160_12Ch(1)
    renderer = MovingHeadRenderer(fixture)
    dims = _moving_head_dimensions(renderer.cube_size)

    # Base center in pre-orientation fixture-local frame. ``render_rectangular_box``
    # treats its ``y`` argument as the box BOTTOM, so the base rendered at
    # ``y = base_height/2`` spans [base_height/2, 3*base_height/2] → center at
    # y = base_height.
    base_center_local = np.array([0.0, dims.base_height, 0.0], dtype=np.float32)

    # Floor mover at z=0.016m, rotation=0
    pos_floor = (0.0, 0.016, 3.0)
    orient_floor = venue_rotation_to_desktop_quaternion(0.0, 0.0, 0.0)
    base_floor = np.array(pos_floor) + quaternion_rotate_vector(
        orient_floor, base_center_local
    )
    head_floor = np.array(_head_pivot_world(pos_floor, orient_floor, dims))
    assert head_floor[1] > base_floor[1], (
        f"floor mover head (y={head_floor[1]:.3f}) must sit ABOVE base "
        f"(y={base_floor[1]:.3f})"
    )

    # Truss mover at z=9.36m, rotation_x=π (upside-down)
    pos_truss = (0.0, 9.36, 3.0)
    orient_truss = venue_rotation_to_desktop_quaternion(math.pi, 0.0, 0.0)
    base_truss = np.array(pos_truss) + quaternion_rotate_vector(
        orient_truss, base_center_local
    )
    head_truss = np.array(_head_pivot_world(pos_truss, orient_truss, dims))
    assert head_truss[1] < base_truss[1], (
        f"truss mover head (y={head_truss[1]:.3f}) must hang BELOW base "
        f"(y={base_truss[1]:.3f})"
    )

    # Sanity: the head should also stay within a reasonable vertical band of
    # the fixture pivot (not flung hundreds of millimetres away as before).
    assert abs(head_floor[1] - pos_floor[1]) < 0.5
    assert abs(head_truss[1] - pos_truss[1]) < 0.5


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
    """Test that BulbRenderer.render_opaque() executes without error"""
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
    renderer.render_opaque(ctx, (1200.0, 1200.0), frame)

    # Cleanup
    fbo.release()
    ctx.release()


def test_renderer_render_moving_head():
    """Test that MovingHeadRenderer.render_opaque() executes without error"""
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
    renderer.render_opaque(ctx, (1200.0, 1200.0), frame)

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

    # Render both opaque and emissive passes
    renderer.render_opaque(ctx, (500.0, 500.0), frame)
    renderer.render_emissive(ctx, (500.0, 500.0), frame)

    # Test with low dimmer (should not render beam)
    fixture.set_dimmer(10)  # Very low dimmer
    renderer.render_opaque(ctx, (500.0, 500.0), frame)
    renderer.render_emissive(ctx, (500.0, 500.0), frame)

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
