#!/usr/bin/env python3

import pytest
from unittest.mock import Mock
from parrot.vj.nodes.glow_effect import GlowEffect
from parrot.vj.nodes.black import Black
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.graph.BaseInterpretationNode import Vibe
from parrot.director.mode import Mode


class TestGlowEffect:
    """Test cases for the GlowEffect node."""

    def setup_method(self):
        self.mock_frame = Mock(spec=Frame)
        self.mock_scheme = Mock(spec=ColorScheme)
        self.black_input = Black()

    def test_initialization_defaults(self):
        """Test GlowEffect initialization with defaults"""
        glow = GlowEffect(self.black_input)

        assert glow.base_intensity == 0.3
        assert glow.max_intensity == 0.8
        assert glow.glow_radius == 8.0
        assert glow.threshold == 0.6
        assert glow.signal == FrameSignal.sustained_low

    def test_initialization_custom_params(self):
        """Test GlowEffect initialization with custom parameters"""
        glow = GlowEffect(
            self.black_input,
            base_intensity=0.2,
            max_intensity=0.9,
            glow_radius=10.0,
            threshold=0.5,
            signal=FrameSignal.freq_high,
        )

        assert glow.base_intensity == 0.2
        assert glow.max_intensity == 0.9
        assert glow.glow_radius == 10.0
        assert glow.threshold == 0.5
        assert glow.signal == FrameSignal.freq_high

    def test_generate_randomizes_parameters(self):
        """Test that generate randomizes glow parameters"""
        glow = GlowEffect(self.black_input)
        original_intensity = glow.base_intensity
        original_radius = glow.glow_radius

        vibe = Vibe(Mode.chill)
        glow.generate(vibe)

        # Parameters should be randomized (very likely to be different)
        # We can't guarantee they're different due to randomness, but we can check they're in valid ranges
        assert 0.2 <= glow.base_intensity <= 0.5
        assert 0.6 <= glow.max_intensity <= 0.9
        assert 6.0 <= glow.glow_radius <= 12.0
        assert 0.4 <= glow.threshold <= 0.7

    def test_print_self_format(self):
        """Test that print_self returns properly formatted string"""
        glow = GlowEffect(self.black_input, max_intensity=0.7, glow_radius=9.5)
        result = glow.print_self()

        assert "GlowEffect" in result
        assert "0.70" in result  # max_intensity
        assert "9.5" in result  # glow_radius
        assert glow.signal.name in result

    def test_fragment_shader_contains_required_elements(self):
        """Test that fragment shader contains required uniforms and logic"""
        glow = GlowEffect(self.black_input)
        shader = glow._get_fragment_shader()

        # Check for required uniforms
        assert "uniform sampler2D input_texture" in shader
        assert "uniform float glow_intensity" in shader
        assert "uniform float glow_radius" in shader
        assert "uniform float glow_threshold" in shader
        assert "uniform vec2 texture_size" in shader

        # Check for main function and basic glow logic
        assert "void main()" in shader
        assert "texture(input_texture, uv)" in shader
        assert "luminance" in shader
        assert "blur" in shader

    def test_set_effect_uniforms_signal_response(self):
        """Test that uniforms are set correctly based on signal"""
        glow = GlowEffect(
            self.black_input,
            base_intensity=0.2,
            max_intensity=0.8,
            signal=FrameSignal.freq_low,
        )

        # Mock shader program with __setitem__ method
        glow.shader_program = Mock()
        glow.shader_program.__setitem__ = Mock()
        glow.framebuffer = Mock()
        glow.framebuffer.width = 1920
        glow.framebuffer.height = 1080

        # Test with low signal
        frame = Frame({FrameSignal.freq_low: 0.0})
        glow._set_effect_uniforms(frame, self.mock_scheme)

        # Should set base intensity when signal is 0
        glow.shader_program.__setitem__.assert_any_call("glow_intensity", 0.2)

        # Test with high signal
        frame = Frame({FrameSignal.freq_low: 1.0})
        glow._set_effect_uniforms(frame, self.mock_scheme)

        # Should set max intensity when signal is 1
        glow.shader_program.__setitem__.assert_any_call("glow_intensity", 0.8)

    def test_set_effect_uniforms_all_parameters(self):
        """Test that all uniforms are set correctly"""
        glow = GlowEffect(self.black_input, glow_radius=10.0, threshold=0.5)

        # Mock shader program and framebuffer
        glow.shader_program = Mock()
        glow.shader_program.__setitem__ = Mock()
        glow.framebuffer = Mock()
        glow.framebuffer.width = 800
        glow.framebuffer.height = 600

        frame = Frame({FrameSignal.sustained_low: 0.5})
        glow._set_effect_uniforms(frame, self.mock_scheme)

        # Check all uniforms are set
        glow.shader_program.__setitem__.assert_any_call("glow_radius", 10.0)
        glow.shader_program.__setitem__.assert_any_call("glow_threshold", 0.5)
        glow.shader_program.__setitem__.assert_any_call("texture_size", (800.0, 600.0))

    def test_set_effect_uniforms_no_framebuffer(self):
        """Test uniform setting when framebuffer is None"""
        glow = GlowEffect(self.black_input)
        glow.shader_program = Mock()
        glow.shader_program.__setitem__ = Mock()
        glow.framebuffer = None

        frame = Frame({FrameSignal.sustained_low: 0.5})
        glow._set_effect_uniforms(frame, self.mock_scheme)

        # Should use default texture size
        glow.shader_program.__setitem__.assert_any_call(
            "texture_size", (1920.0, 1080.0)
        )
