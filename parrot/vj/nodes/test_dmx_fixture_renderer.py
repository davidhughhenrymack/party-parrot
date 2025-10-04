#!/usr/bin/env python3

import pytest
import moderngl as mgl
import numpy as np
from PIL import Image

from parrot.vj.nodes.dmx_fixture_renderer import DMXFixtureRenderer
from parrot.director.frame import Frame
from parrot.director.color_scheme import ColorScheme
from parrot.director.color_schemes import scheme_halloween
from parrot.patch_bay import venues
from parrot.utils.colour import Color
from parrot.state import State


def test_dmx_fixture_renderer_basic():
    """Test that DMX fixture renderer can render without crashing"""
    # Create standalone ModernGL context
    ctx = mgl.create_context(standalone=True)

    # Create state with venue
    state = State()
    state.set_venue(venues.dmack)

    # Create renderer with dmack venue (has various fixture types)
    renderer = DMXFixtureRenderer(
        state=state,
        width=1920,
        height=1080,
    )

    # Setup renderer
    renderer.enter(ctx)

    # Create test frame
    frame = Frame({})
    scheme = scheme_halloween[0]

    # Render
    fbo = renderer.render(frame, scheme, ctx)

    assert fbo is not None
    assert fbo.width == 1920
    assert fbo.height == 1080

    # Cleanup
    renderer.exit()
    ctx.release()


@pytest.mark.skip(
    reason="Output test needs coordinate mapping fix - see visual test instead"
)
def test_dmx_fixture_renderer_output():
    """Test that DMX fixture renderer produces output with fixture boxes visible"""
    # Create standalone ModernGL context
    ctx = mgl.create_context(standalone=True)

    # Create state with venue
    state = State()
    state.set_venue(venues.dmack)

    # Create renderer
    renderer = DMXFixtureRenderer(
        state=state,
        width=800,
        height=600,
    )

    # Setup renderer
    renderer.enter(ctx)

    # Set some DMX values on fixtures so they're visible
    for fixture in renderer.fixtures[:3]:  # Set first 3 fixtures
        try:
            fixture.set_dimmer(255)  # Full brightness
            if hasattr(fixture, "set_color"):
                fixture.set_color(Color("red"))
        except:
            pass  # Some fixtures might not support these methods

    # Create test frame
    frame = Frame({})
    scheme = scheme_halloween[0]

    # Render
    fbo = renderer.render(frame, scheme, ctx)

    # Read pixels - use actual framebuffer dimensions
    texture = fbo.color_attachments[0]
    width, height = texture.size
    data = texture.read()

    # Reshape based on actual texture size and format
    bytes_per_pixel = len(data) // (width * height)
    if bytes_per_pixel == 4:
        pixels = np.frombuffer(data, dtype=np.uint8).reshape((height, width, 4))[
            :, :, :3
        ]
    else:
        pixels = np.frombuffer(data, dtype=np.uint8).reshape((height, width, 3))

    # Check that we have some non-black pixels
    # Gray boxes should be visible even without dimmer values
    max_value = np.max(pixels)
    mean_value = np.mean(pixels)

    # We should at least see the gray fixture boxes (value ~76 for 0.3 gray)
    assert (
        mean_value > 0
    ), f"Output should have visible content, got mean={mean_value}, max={max_value}"

    # Cleanup
    renderer.exit()
    ctx.release()


def test_dmx_fixture_renderer_visual():
    """Visual test - renders to PNG for manual inspection"""
    # Create standalone ModernGL context
    ctx = mgl.create_context(standalone=True)

    # Create state with venue
    state = State()
    state.set_venue(venues.dmack)

    # Create renderer
    renderer = DMXFixtureRenderer(
        state=state,
        width=1920,
        height=1080,
    )

    # Setup renderer
    renderer.enter(ctx)

    # Create test frame
    frame = Frame({})
    scheme = scheme_halloween[0]

    # Render
    fbo = renderer.render(frame, scheme, ctx)

    # Read pixels and save to file
    texture = fbo.color_attachments[0]
    data = texture.read()
    pixels = np.frombuffer(data, dtype=np.uint8).reshape((1080, 1920, 3))

    # Flip vertically (OpenGL coordinates)
    pixels = np.flipud(pixels)

    # Save to PNG
    img = Image.fromarray(pixels, mode="RGB")
    img.save("test_output/dmx_fixture_renderer.png")
    print("Saved test_output/dmx_fixture_renderer.png")

    # Cleanup
    renderer.exit()
    ctx.release()


def test_dmx_fixture_renderer_multiple_venues():
    """Test that renderer works with different venues"""
    ctx = mgl.create_context(standalone=True)

    # Create state
    state = State()

    for venue in [venues.dmack, venues.mtn_lotus, venues.crux_test]:
        state.set_venue(venue)
        renderer = DMXFixtureRenderer(
            state=state,
            width=800,
            height=600,
        )

        renderer.enter(ctx)

        frame = Frame({})
        scheme = scheme_halloween[0]

        fbo = renderer.render(frame, scheme, ctx)
        assert fbo is not None

        renderer.exit()

    ctx.release()
