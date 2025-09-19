#!/usr/bin/env python3

import time
import pytest
from unittest.mock import Mock

from parrot.vj.nodes.text_color_pulse import TextColorPulse
from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode
from parrot.utils.colour import Color


class MockInputNode(BaseInterpretationNode):
    """Mock input node for testing"""

    def __init__(self):
        super().__init__([])

    def enter(self, context):
        pass

    def exit(self):
        pass

    def generate(self, vibe):
        pass

    def render(self, frame, scheme, context):
        return None


class TestTextColorPulse:
    """Test TextColorPulse effect node"""

    def test_initialization(self):
        """Test that TextColorPulse initializes with correct defaults"""
        mock_input = MockInputNode()
        effect = TextColorPulse(mock_input)

        assert effect.intensity == 1.0
        assert effect.decay_rate == 0.95
        assert effect.signal == FrameSignal.pulse
        assert effect.current_pulse_intensity == 0.0
        assert effect.current_color_index == 0
        assert effect.color_change_threshold == 0.7

    def test_custom_parameters(self):
        """Test TextColorPulse with custom parameters"""
        mock_input = MockInputNode()
        effect = TextColorPulse(
            mock_input, intensity=0.8, decay_rate=0.9, signal=FrameSignal.freq_high
        )

        assert effect.intensity == 0.8
        assert effect.decay_rate == 0.9
        assert effect.signal == FrameSignal.freq_high

    def test_generate_randomizes_parameters(self):
        """Test that generate() randomizes effect parameters"""
        mock_input = MockInputNode()
        effect = TextColorPulse(mock_input)
        vibe = Vibe(Mode.rave)

        # Store original values
        original_signal = effect.signal
        original_intensity = effect.intensity
        original_decay_rate = effect.decay_rate
        original_threshold = effect.color_change_threshold

        # Generate new parameters
        effect.generate(vibe)

        # At least some parameters should change (with high probability)
        # We can't guarantee all will change due to randomness, but signal should be from the expected list
        pulse_signals = [
            FrameSignal.pulse,
            FrameSignal.freq_low,
            FrameSignal.freq_high,
            FrameSignal.freq_all,
            FrameSignal.sustained_low,
            FrameSignal.sustained_high,
        ]
        assert effect.signal in pulse_signals
        assert 0.6 <= effect.intensity <= 1.0
        assert 0.85 <= effect.decay_rate <= 0.98
        assert 0.5 <= effect.color_change_threshold <= 0.8

    def test_pulse_state_buildup(self):
        """Test that pulse intensity builds up during strong signals"""
        mock_input = MockInputNode()
        effect = TextColorPulse(mock_input, intensity=1.0)

        # Create frame with strong pulse signal
        frame_values = {signal: 0.0 for signal in FrameSignal}
        frame_values[FrameSignal.pulse] = 0.8
        frame = Frame(frame_values)

        # Create color scheme
        scheme = ColorScheme(Color("red"), Color("blue"), Color("green"))

        # Update pulse state
        effect._update_pulse_state(frame)

        # Pulse intensity should increase
        assert effect.current_pulse_intensity > 0.0

    def test_pulse_state_decay(self):
        """Test that pulse intensity decays during weak signals"""
        mock_input = MockInputNode()
        effect = TextColorPulse(mock_input, decay_rate=0.5)  # Fast decay for testing

        # Set initial pulse intensity
        effect.current_pulse_intensity = 0.8

        # Create frame with weak pulse signal
        frame_values = {signal: 0.0 for signal in FrameSignal}
        frame_values[FrameSignal.pulse] = 0.1
        frame = Frame(frame_values)

        # Update pulse state multiple times to see decay
        for _ in range(10):
            effect._update_pulse_state(frame)
            time.sleep(0.01)  # Small delay to simulate time passing

        # Pulse intensity should decrease
        assert effect.current_pulse_intensity < 0.8

    def test_color_cycling(self):
        """Test that colors cycle through color scheme"""
        mock_input = MockInputNode()
        effect = TextColorPulse(mock_input)
        effect.color_change_threshold = 0.5

        # Create color scheme
        scheme = ColorScheme(Color("red"), Color("blue"), Color("green"))

        # Test color selection for each index
        effect.current_color_index = 0
        color0 = effect._get_pulse_color(scheme)
        assert color0 == scheme.fg.rgb

        effect.current_color_index = 1
        color1 = effect._get_pulse_color(scheme)
        assert color1 == scheme.bg.rgb

        effect.current_color_index = 2
        color2 = effect._get_pulse_color(scheme)
        assert color2 == scheme.bg_contrast.rgb

    def test_color_change_on_strong_pulse(self):
        """Test that color index changes on strong pulse signals"""
        mock_input = MockInputNode()
        effect = TextColorPulse(mock_input)
        effect.color_change_threshold = 0.6

        initial_color_index = effect.current_color_index

        # Create frame with strong pulse signal (above threshold)
        frame_values = {signal: 0.0 for signal in FrameSignal}
        frame_values[FrameSignal.pulse] = 0.8
        frame = Frame(frame_values)

        # Update pulse state
        effect._update_pulse_state(frame)

        # Color index should have changed
        assert effect.current_color_index != initial_color_index

    def test_fragment_shader_generation(self):
        """Test that fragment shader is generated correctly"""
        mock_input = MockInputNode()
        effect = TextColorPulse(mock_input)

        shader_source = effect._get_fragment_shader()

        # Check that shader contains expected uniforms and logic
        assert "uniform sampler2D input_texture" in shader_source
        assert "uniform vec3 pulse_color" in shader_source
        assert "uniform float pulse_intensity" in shader_source
        assert "uniform float color_mix_factor" in shader_source
        assert "luminance" in shader_source  # Text detection logic
        assert "mix(" in shader_source  # Color mixing logic

    def test_set_effect_uniforms(self):
        """Test that effect uniforms are set correctly"""
        mock_input = MockInputNode()
        effect = TextColorPulse(mock_input)

        # Mock shader program
        effect.shader_program = Mock()
        effect.shader_program.__setitem__ = Mock()

        # Create test frame and scheme
        frame_values = {signal: 0.0 for signal in FrameSignal}
        frame_values[FrameSignal.pulse] = 0.5
        frame = Frame(frame_values)
        scheme = ColorScheme(Color("red"), Color("blue"), Color("green"))

        # Set uniforms
        effect._set_effect_uniforms(frame, scheme)

        # Verify that uniforms were set
        assert (
            effect.shader_program.__setitem__.call_count >= 3
        )  # At least 3 uniforms should be set
