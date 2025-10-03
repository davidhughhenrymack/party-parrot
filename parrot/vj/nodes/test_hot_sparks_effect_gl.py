#!/usr/bin/env python3

import pytest
import moderngl as mgl
from parrot.vj.nodes.hot_sparks_effect import HotSparksEffect
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.utils.colour import Color


@pytest.fixture
def gl_context():
    """Create a headless OpenGL context for testing"""
    return mgl.create_context(standalone=True)


@pytest.fixture
def color_scheme():
    """Create a test color scheme"""
    orange_color = Color()
    orange_color.rgb = (1.0, 0.5, 0.0)

    black_color = Color()
    black_color.rgb = (0.0, 0.0, 0.0)

    blue_color = Color()
    blue_color.rgb = (0.0, 0.5, 1.0)

    return ColorScheme(fg=orange_color, bg=black_color, bg_contrast=blue_color)


def test_hot_sparks_gl_setup(gl_context):
    """Test OpenGL resource setup"""
    sparks = HotSparksEffect(width=256, height=256)

    # Initially no GL resources
    assert sparks.framebuffer is None
    assert sparks.texture is None
    assert sparks.shader_program is None
    assert sparks.quad_vao is None

    # Enter should set up GL resources
    sparks.enter(gl_context)

    assert sparks.framebuffer is not None
    assert sparks.texture is not None
    assert sparks.shader_program is not None
    assert sparks.quad_vao is not None

    # Exit should clean up
    sparks.exit()

    assert sparks.framebuffer is None
    assert sparks.texture is None
    assert sparks.shader_program is None
    assert sparks.quad_vao is None


def test_hot_sparks_render_no_signal(gl_context, color_scheme):
    """Test rendering with no signal (should render black)"""
    sparks = HotSparksEffect(width=256, height=256)

    # Frame with no signal
    frame = Frame({FrameSignal.small_blinder: 0.0})

    # Render
    result = sparks.render(frame, color_scheme, gl_context)

    # Should return a framebuffer
    assert result is not None
    assert result.width == 256
    assert result.height == 256


def test_hot_sparks_render_with_pulse(gl_context, color_scheme):
    """Test rendering with pulse signal (should render sparks)"""
    sparks = HotSparksEffect(width=256, height=256, num_sparks=20)

    # Frame with strong signal to trigger pulse
    frame = Frame({FrameSignal.small_blinder: 0.9})

    # Render first frame (trigger pulse)
    result = sparks.render(frame, color_scheme, gl_context)
    assert result is not None

    # Render second frame (sparks should be animating)
    frame2 = Frame({FrameSignal.small_blinder: 0.8})
    result2 = sparks.render(frame2, color_scheme, gl_context)
    assert result2 is not None


def test_hot_sparks_shader_compilation(gl_context):
    """Test that shader compiles without errors"""
    sparks = HotSparksEffect(width=256, height=256)
    sparks.enter(gl_context)

    # Shader should compile successfully
    assert sparks.shader_program is not None

    # Check that required uniforms exist
    uniforms = set(sparks.shader_program)
    expected_uniforms = {
        "time",
        "emission_start_time",
        "pulse_seed",
        "num_sparks",
        "spark_lifetime",
        "spark_color",
    }

    # All expected uniforms should be present
    assert expected_uniforms.issubset(uniforms)

    sparks.exit()
