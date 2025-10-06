#!/usr/bin/env python3

import pytest
from unittest.mock import Mock
from parrot.vj.nodes.hot_sparks_effect import HotSparksEffect
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.utils.colour import Color
from parrot.graph.BaseInterpretationNode import Vibe
from parrot.director.mode import Mode


class TestHotSparksEffect:
    """Test cases for the HotSparksEffect node."""

    def setup_method(self):
        self.mock_frame = Mock(spec=Frame)
        self.mock_scheme = Mock(spec=ColorScheme)
        fg_color = Color()
        fg_color.rgb = (1.0, 0.5, 0.25)  # Orange foreground color
        self.mock_scheme.fg = fg_color

    def test_initialization_defaults(self):
        """Test HotSparksEffect initialization with defaults"""
        sparks = HotSparksEffect()

        assert sparks.width == 1920
        assert sparks.height == 1080
        assert sparks.num_sparks == 600
        assert sparks.spark_lifetime == 1.0
        assert sparks.signal == FrameSignal.pulse
        assert sparks.mode_opacity_multiplier == 1.0

    def test_initialization_custom_params(self):
        """Test HotSparksEffect initialization with custom parameters"""
        sparks = HotSparksEffect(
            width=800,
            height=600,
            num_sparks=60,
            spark_lifetime=2.0,
            signal=FrameSignal.pulse,
            opacity_multiplier=0.5,
        )

        assert sparks.width == 800
        assert sparks.height == 600
        assert sparks.num_sparks == 60
        assert sparks.spark_lifetime == 2.0
        assert sparks.signal == FrameSignal.pulse
        assert sparks.mode_opacity_multiplier == 0.5

    def test_generate_vibe_energetic(self):
        """Test that generate works with rave vibe"""
        sparks = HotSparksEffect(num_sparks=500, opacity_multiplier=1.0)
        vibe = Vibe(Mode.rave)
        sparks.generate(vibe)
        # Parameters should remain as set in init
        assert sparks.num_sparks == 500
        assert sparks.mode_opacity_multiplier == 1.0

    def test_generate_vibe_chill(self):
        """Test that generate works with chill vibe"""
        sparks = HotSparksEffect(num_sparks=200, opacity_multiplier=0.3)
        vibe = Vibe(Mode.chill)
        sparks.generate(vibe)
        # Parameters should remain as set in init
        assert sparks.num_sparks == 200
        assert sparks.mode_opacity_multiplier == 0.3

    def test_print_self_format(self):
        """Test that print_self returns properly formatted string"""
        sparks = HotSparksEffect()
        result = sparks.print_self()

        assert "HotSparksEffect" in result
        assert "✨" in result  # Sparkle emoji
        assert sparks.signal.name in result

    def test_fragment_shader_contains_required_elements(self):
        """Test that fragment shader contains required uniforms and logic"""
        sparks = HotSparksEffect()
        shader = sparks._get_fragment_shader()

        # Check for required uniforms
        assert "uniform float time" in shader
        assert "uniform float emission_start_time" in shader
        assert "uniform float pulse_seed" in shader
        assert "uniform int num_sparks" in shader
        assert "uniform float spark_lifetime" in shader
        assert "uniform float mode_opacity_multiplier" in shader

        # Check for main function and basic spark logic
        assert "void main()" in shader
        assert "calculate_spark" in shader
        assert "random" in shader
        assert "rounded_rect" in shader
        assert "rotate2d" in shader

    def test_set_effect_uniforms_basic(self):
        """Test that uniforms are set correctly"""
        sparks = HotSparksEffect(num_sparks=30, spark_lifetime=1.0)

        # Mock shader program
        sparks.shader_program = Mock()
        sparks.shader_program.__setitem__ = Mock()

        frame = Frame({FrameSignal.small_blinder: 0.8})
        sparks._set_effect_uniforms(frame, self.mock_scheme)

        # Check uniforms are set
        sparks.shader_program.__setitem__.assert_any_call("num_sparks", 30)
        sparks.shader_program.__setitem__.assert_any_call("spark_lifetime", 1.0)

    def test_set_effect_uniforms_uses_opacity(self):
        """Test that spark uniforms include opacity multiplier"""
        sparks = HotSparksEffect(opacity_multiplier=0.5)

        # Mock shader program
        sparks.shader_program = Mock()
        sparks.shader_program.__setitem__ = Mock()

        # Create mock color scheme
        mock_scheme = Mock(spec=ColorScheme)
        mock_fg_color = Mock()
        mock_fg_color.rgb = (1.0, 0.5, 0.25)
        mock_scheme.fg = mock_fg_color

        frame = Frame({FrameSignal.pulse: 0.5})
        sparks._set_effect_uniforms(frame, mock_scheme)

        # Check opacity multiplier is set
        sparks.shader_program.__setitem__.assert_any_call(
            "mode_opacity_multiplier", 0.5
        )

    def test_pulse_detection(self):
        """Test that emission starts when signal goes high"""
        sparks = HotSparksEffect()

        # Mock shader program
        sparks.shader_program = Mock()
        sparks.shader_program.__setitem__ = Mock()

        # First frame with low signal
        frame1 = Frame({FrameSignal.pulse: 0.0})
        sparks._set_effect_uniforms(frame1, self.mock_scheme)
        assert not sparks.is_emitting
        emission_time_1 = sparks.emission_start_time

        # Second frame with high signal (should start emission)
        frame2 = Frame({FrameSignal.pulse: 0.8})
        sparks._set_effect_uniforms(frame2, self.mock_scheme)
        assert sparks.is_emitting
        emission_time_2 = sparks.emission_start_time

        # Emission time should have changed
        assert emission_time_2 > emission_time_1

    def test_pulse_cooldown(self):
        """Test that emission continues while signal stays high"""
        sparks = HotSparksEffect()

        # Mock shader program
        sparks.shader_program = Mock()
        sparks.shader_program.__setitem__ = Mock()

        # Start emission
        frame1 = Frame({FrameSignal.pulse: 0.8})
        sparks._set_effect_uniforms(frame1, self.mock_scheme)
        emission_time_1 = sparks.emission_start_time
        assert sparks.is_emitting

        # Signal stays high (emission should continue with same start time)
        frame2 = Frame({FrameSignal.pulse: 0.9})
        sparks._set_effect_uniforms(frame2, self.mock_scheme)
        emission_time_2 = sparks.emission_start_time

        # Emission time should be the same (continuous emission)
        assert emission_time_2 == emission_time_1
        assert sparks.is_emitting
