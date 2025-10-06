#!/usr/bin/env python3

import pytest
import numpy as np
import moderngl as mgl
from unittest.mock import Mock

from parrot.vj.nodes.oscilloscope_effect import OscilloscopeEffect
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode
from parrot.graph.BaseInterpretationNode import Vibe
from parrot.utils.colour import Color


def test_oscilloscope_effect_creation():
    """Test that OscilloscopeEffect can be created with default parameters"""
    effect = OscilloscopeEffect()
    assert effect.line_count == 8
    assert effect.scroll_speed == 2.0
    assert effect.waveform_scale == 0.3
    assert effect.bloom_intensity == 1.5
    assert effect.signal == FrameSignal.freq_all


def test_oscilloscope_effect_custom_parameters():
    """Test that OscilloscopeEffect can be created with custom parameters"""
    effect = OscilloscopeEffect(
        width=1280,
        height=720,
        line_count=12,
        scroll_speed=3.0,
        waveform_scale=0.5,
        bloom_intensity=2.0,
        signal=FrameSignal.freq_low,
    )
    assert effect.width == 1280
    assert effect.height == 720
    assert effect.line_count == 12
    assert effect.scroll_speed == 3.0
    assert effect.waveform_scale == 0.5
    assert effect.bloom_intensity == 2.0
    assert effect.signal == FrameSignal.freq_low


def test_oscilloscope_effect_generate():
    """Test that generate method works and can randomize parameters"""
    effect = OscilloscopeEffect()
    original_line_count = effect.line_count

    vibe = Vibe(Mode.chill)

    # Call generate multiple times to test randomization
    for _ in range(10):
        effect.generate(vibe)
        # Parameters should be within expected ranges
        assert 6 <= effect.line_count <= 12
        assert 1.0 <= effect.scroll_speed <= 3.0
        assert 0.2 <= effect.waveform_scale <= 0.5
        assert 1.0 <= effect.bloom_intensity <= 2.0


def test_waveform_history_update():
    """Test that waveform history is updated correctly with audio data"""
    effect = OscilloscopeEffect()

    # Create mock frame with audio timeseries data
    audio_data = np.sin(np.linspace(0, 4 * np.pi, 100))  # Sine wave
    frame = Frame(
        values={FrameSignal.freq_all: 0.5},
        timeseries={FrameSignal.freq_all.name: audio_data},
    )

    # Update waveform history
    effect._update_waveform_history(frame)

    # Check that history was updated
    assert len(effect.waveform_history) > 0
    assert isinstance(effect.waveform_history[0], (float, np.floating))

    # Check that data is normalized to [-1, 1] range
    history_array = np.array(effect.waveform_history)
    assert np.all(history_array >= -1.0)
    assert np.all(history_array <= 1.0)


def test_waveform_history_fallback():
    """Test that fallback waveform is generated when no audio data is available"""
    effect = OscilloscopeEffect()

    # Create frame without timeseries data
    frame = Frame(values={FrameSignal.freq_all: 0.5})

    # Update waveform history
    effect._update_waveform_history(frame)

    # Check that fallback data was generated
    assert len(effect.waveform_history) > 0
    assert isinstance(effect.waveform_history[0], (float, np.floating))


def test_waveform_history_max_length():
    """Test that waveform history is kept within max length"""
    effect = OscilloscopeEffect()
    effect.max_history_length = 50  # Set small limit for testing

    # Add more data than the limit
    large_audio_data = np.sin(np.linspace(0, 10 * np.pi, 200))
    frame = Frame(
        values={FrameSignal.freq_all: 0.5},
        timeseries={FrameSignal.freq_all.name: large_audio_data},
    )

    effect._update_waveform_history(frame)

    # Check that history is limited
    assert len(effect.waveform_history) <= effect.max_history_length


def test_shader_generation():
    """Test that shaders can be generated without errors"""
    effect = OscilloscopeEffect()

    # Test main fragment shader
    fragment_shader = effect._get_fragment_shader()
    assert isinstance(fragment_shader, str)
    assert "#version 330 core" in fragment_shader
    assert "waveform_data" in fragment_shader
    assert (
        "oscilloscope" in fragment_shader.lower()
        or "waveform" in fragment_shader.lower()
    )

    # Check that glow has reduced alpha values
    assert "* 0.6" in fragment_shader  # Reduced glow intensity
    assert "* 0.4" in fragment_shader  # Reduced core glow
    assert "* 0.05" in fragment_shader  # Reduced intensity contribution

    # Test blur fragment shader
    blur_shader = effect._get_blur_fragment_shader()
    assert isinstance(blur_shader, str)
    assert "#version 330 core" in blur_shader
    assert "blur" in blur_shader.lower()

    # Test composite fragment shader
    composite_shader = effect._get_composite_fragment_shader()
    assert isinstance(composite_shader, str)
    assert "#version 330 core" in composite_shader
    assert "bloom" in composite_shader.lower()


def test_color_scheme_integration():
    """Test that the effect properly uses background color from color scheme"""
    effect = OscilloscopeEffect()

    # Create a test color scheme with distinct colors
    scheme = ColorScheme(
        fg=Color("red"),  # RGB: (255, 0, 0)
        bg=Color("blue"),  # RGB: (0, 0, 255)
        bg_contrast=Color("green"),  # RGB: (0, 255, 0)
    )

    # Create a mock frame
    frame = Frame(values={FrameSignal.freq_all: 0.5})

    # Mock the shader program to capture uniform values
    mock_shader = Mock()
    uniform_values = {}

    def mock_setitem(self, key, value):
        uniform_values[key] = value

    mock_shader.__setitem__ = mock_setitem
    effect.shader_program = mock_shader
    effect.waveform_history = [0.0, 0.1, 0.2]  # Some test data

    # Mock the _bind_waveform_texture method since we don't have OpenGL context
    effect._bind_waveform_texture = Mock()

    # Call the method that sets uniforms
    effect._set_effect_uniforms(frame, scheme)

    # Verify that base_color was set and incorporates background color
    base_color_call = uniform_values.get("base_color")

    assert base_color_call is not None, "base_color uniform should be set"

    # Updated base color calculation uses 0.4*bg + 0.6*fg
    red_rgb = list(scheme.fg.rgb)
    blue_rgb = list(scheme.bg.rgb)
    expected_r = 0.4 * blue_rgb[0] + 0.6 * red_rgb[0]
    expected_g = 0.4 * blue_rgb[1] + 0.6 * red_rgb[1]
    expected_b = 0.4 * blue_rgb[2] + 0.6 * red_rgb[2]

    assert (
        abs(base_color_call[0] - expected_r) < 0.01
    ), f"Red component should be ~{expected_r}, got {base_color_call[0]}"
    assert (
        abs(base_color_call[1] - expected_g) < 0.01
    ), f"Green component should be ~{expected_g}, got {base_color_call[1]}"
    assert (
        abs(base_color_call[2] - expected_b) < 0.01
    ), f"Blue component should be ~{expected_b}, got {base_color_call[2]}"


if __name__ == "__main__":
    pytest.main([__file__])
