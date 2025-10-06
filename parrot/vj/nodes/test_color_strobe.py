#!/usr/bin/env python3

import pytest
import moderngl as mgl
import time
from unittest.mock import Mock

from parrot.vj.nodes.color_strobe import ColorStrobe
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.utils.colour import Color
from parrot.graph.BaseInterpretationNode import Vibe


@pytest.fixture
def gl_context():
    """Create a headless OpenGL context for testing"""
    return mgl.create_context(standalone=True)


@pytest.fixture
def color_scheme():
    """Create a test color scheme"""
    red_color = Color()
    red_color.rgb = (1.0, 0.0, 0.0)  # Red foreground

    black_color = Color()
    black_color.rgb = (0.0, 0.0, 0.0)  # Black background

    green_color = Color()
    green_color.rgb = (0.0, 1.0, 0.0)  # Green contrast

    return ColorScheme(fg=red_color, bg=black_color, bg_contrast=green_color)


@pytest.fixture
def frame():
    """Create a test frame with default signal values"""
    frame = Mock(spec=Frame)
    frame.__getitem__ = Mock(return_value=0.0)  # Default all signals to 0
    return frame


def test_color_strobe_initialization():
    """Test ColorStrobe node initialization"""
    strobe = ColorStrobe()

    assert strobe.width == 1280  # DEFAULT_WIDTH
    assert strobe.height == 720  # DEFAULT_HEIGHT
    assert strobe.strobe_frequency == 8.0
    assert strobe.signal == FrameSignal.strobe
    assert strobe.current_color == (0.0, 0.0, 0.0)


def test_color_strobe_custom_parameters():
    """Test ColorStrobe with custom parameters"""
    strobe = ColorStrobe(
        width=800,
        height=600,
        strobe_frequency=12.0,
        signal=FrameSignal.pulse,
    )

    assert strobe.width == 800
    assert strobe.height == 600
    assert strobe.strobe_frequency == 12.0
    assert strobe.signal == FrameSignal.pulse


def test_color_strobe_gl_setup(gl_context):
    """Test OpenGL resource setup"""
    strobe = ColorStrobe(width=256, height=256)

    # Initially no GL resources
    assert strobe.framebuffer is None
    assert strobe.texture is None
    assert strobe.shader_program is None
    assert strobe.quad_vao is None

    # Enter should set up GL resources
    strobe.enter(gl_context)

    assert strobe.framebuffer is not None
    assert strobe.texture is not None
    assert strobe.shader_program is not None
    assert strobe.quad_vao is not None

    # Exit should clean up
    strobe.exit()

    assert strobe.framebuffer is None
    assert strobe.texture is None
    assert strobe.shader_program is None
    assert strobe.quad_vao is None


def test_strobe_color_palette_update(gl_context, color_scheme):
    """Test that strobe colors are updated from color scheme"""
    strobe = ColorStrobe(width=256, height=256)
    strobe.enter(gl_context)

    # Update colors from scheme
    strobe._update_strobe_colors(color_scheme)

    # Should have 6 colors in the palette
    assert len(strobe.strobe_colors) == 6

    # Should include foreground and contrast colors (with floating point tolerance)
    def color_in_list(target_color, color_list, tolerance=1e-10):
        """Check if a color is in the list with floating point tolerance"""
        for color in color_list:
            if all(abs(a - b) < tolerance for a, b in zip(target_color, color)):
                return True
        return False

    assert color_in_list((1.0, 0.0, 0.0), strobe.strobe_colors)  # Red fg
    assert color_in_list((0.0, 1.0, 0.0), strobe.strobe_colors)  # Green contrast
    assert color_in_list((1.0, 1.0, 1.0), strobe.strobe_colors)  # White
    assert color_in_list((0.0, 0.0, 0.0), strobe.strobe_colors)  # Black

    strobe.exit()


def test_strobe_signal_response(gl_context, color_scheme, frame):
    """Test response to strobe signals"""
    strobe = ColorStrobe(width=256, height=256)
    strobe.enter(gl_context)

    # Mock strong strobe signal
    frame.__getitem__.side_effect = lambda signal: (
        1.0 if signal == FrameSignal.strobe else 0.0
    )

    # Render with strobe signal
    result = strobe.render(frame, color_scheme, gl_context)

    assert result is not None
    assert result == strobe.framebuffer

    strobe.exit()


def test_big_blinder_response(gl_context, color_scheme, frame):
    """Test response to big blinder signals"""
    strobe = ColorStrobe(width=256, height=256)
    strobe.enter(gl_context)

    # Mock big blinder signal
    frame.__getitem__.side_effect = lambda signal: (
        0.8 if signal == FrameSignal.big_blinder else 0.0
    )

    # Render with big blinder signal
    result = strobe.render(frame, color_scheme, gl_context)

    assert result is not None
    # Should use white color for big blinder
    assert strobe.current_color == (1.0, 1.0, 1.0)

    strobe.exit()


def test_pulse_response(gl_context, color_scheme, frame):
    """Test that pulse signals are ignored"""
    strobe = ColorStrobe(width=256, height=256)
    strobe.enter(gl_context)

    # Mock pulse signal
    frame.__getitem__.side_effect = lambda signal: (
        0.7 if signal == FrameSignal.pulse else 0.0
    )

    # Render with pulse signal
    result = strobe.render(frame, color_scheme, gl_context)

    assert result is not None
    # Should remain black/invisible since pulse signals are ignored
    assert strobe.current_color == (0.0, 0.0, 0.0)

    strobe.exit()


def test_no_signal_response(gl_context, color_scheme, frame):
    """Test behavior with no signals"""
    strobe = ColorStrobe(width=256, height=256)
    strobe.enter(gl_context)

    # All signals at 0
    frame.__getitem__.return_value = 0.0

    # Render with no signals
    result = strobe.render(frame, color_scheme, gl_context)

    assert result is not None
    # Should remain black/invisible
    assert strobe.current_color == (0.0, 0.0, 0.0)

    strobe.exit()


def test_vibe_adaptation():
    """Test that strobe adapts to different vibes"""
    from parrot.director.mode import Mode

    # Test rave mode configuration
    rave_strobe = ColorStrobe(strobe_frequency=12.0, opacity_multiplier=1.0)
    rave_vibe = Vibe(mode=Mode.rave)
    rave_strobe.generate(rave_vibe)
    assert rave_strobe.strobe_frequency == 12.0
    assert rave_strobe.mode_opacity_multiplier == 1.0

    # Test chill mode configuration
    chill_strobe = ColorStrobe(strobe_frequency=4.0, opacity_multiplier=0.2)
    chill_vibe = Vibe(mode=Mode.chill)
    chill_strobe.generate(chill_vibe)
    assert chill_strobe.strobe_frequency == 4.0
    assert chill_strobe.mode_opacity_multiplier == 0.2

    # Test blackout mode configuration
    blackout_strobe = ColorStrobe(strobe_frequency=4.0, opacity_multiplier=0.0)
    blackout_vibe = Vibe(mode=Mode.blackout)
    blackout_strobe.generate(blackout_vibe)
    assert blackout_strobe.strobe_frequency == 4.0
    assert blackout_strobe.mode_opacity_multiplier == 0.0


def test_strobe_color_cycling():
    """Test that strobe colors cycle properly"""
    strobe = ColorStrobe(strobe_frequency=10.0)  # 10 Hz for easy testing

    # Set up test colors
    strobe.strobe_colors = [
        (1.0, 0.0, 0.0),  # Red
        (0.0, 1.0, 0.0),  # Green
        (0.0, 0.0, 1.0),  # Blue
    ]

    # Test color cycling with controlled timing
    # Use a base time of 0 for predictable results
    base_time = 0.0

    # At time 0, should be first color (index 0)
    color1 = strobe._get_strobe_color(base_time)
    assert color1 == (1.0, 0.0, 0.0)

    # At time 0.1 (1/10 second later), should be second color (index 1)
    color2 = strobe._get_strobe_color(base_time + 0.1)
    assert color2 == (0.0, 1.0, 0.0)

    # At time 0.2, should be third color (index 2)
    color3 = strobe._get_strobe_color(base_time + 0.2)
    assert color3 == (0.0, 0.0, 1.0)

    # At time 0.3, we get floating point precision issues, so test 0.31 instead
    # which should definitely cycle back to first color (index 0)
    color4 = strobe._get_strobe_color(base_time + 0.31)
    assert color4 == (1.0, 0.0, 0.0)


def test_headless_rendering(gl_context, color_scheme, frame):
    """Test that the strobe can render without display (headless)"""
    strobe = ColorStrobe(width=64, height=64)  # Small size for speed
    strobe.enter(gl_context)

    # Mock strobe signal
    frame.__getitem__.side_effect = lambda signal: (
        0.8 if signal == FrameSignal.strobe else 0.0
    )

    # Should render without errors
    result = strobe.render(frame, color_scheme, gl_context)
    assert result is not None

    # Should be able to read the framebuffer
    assert result.width == 64
    assert result.height == 64

    strobe.exit()
