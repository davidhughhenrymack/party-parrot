#!/usr/bin/env python3

import pytest
from unittest.mock import Mock, MagicMock

from parrot.vj.nodes.saturation_pulse import SaturationPulse
from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode


class MockInputNode(BaseInterpretationNode):
    """Mock input node for testing"""

    def __init__(self):
        super().__init__([])
        self.render_result = None

    def enter(self, context):
        pass

    def exit(self):
        pass

    def generate(self, vibe):
        pass

    def render(self, frame, scheme, context):
        return self.render_result


class TestSaturationPulse:
    """Test the saturation pulse effect"""

    def test_init_default_params(self):
        """Test initialization with default parameters"""
        input_node = MockInputNode()
        effect = SaturationPulse(input_node)

        assert effect.input_node == input_node
        assert effect.intensity == 0.8
        assert effect.base_saturation == 0.2
        assert effect.signal == FrameSignal.freq_high

    def test_init_custom_params(self):
        """Test initialization with custom parameters"""
        input_node = MockInputNode()
        effect = SaturationPulse(
            input_node,
            intensity=0.5,
            base_saturation=0.1,
            signal=FrameSignal.sustained_high,
        )

        assert effect.intensity == 0.5
        assert effect.base_saturation == 0.1
        assert effect.signal == FrameSignal.sustained_high

    def test_fragment_shader_contains_hsv_functions(self):
        """Test that fragment shader contains HSV conversion functions"""
        input_node = MockInputNode()
        effect = SaturationPulse(input_node)

        shader = effect._get_fragment_shader()

        # Check for key HSV functions and uniforms
        assert "rgb2hsv" in shader
        assert "hsv2rgb" in shader
        assert "saturation_multiplier" in shader
        assert "input_texture" in shader

    def test_signal_parameter_storage(self):
        """Test that signal parameter is stored correctly"""
        input_node = MockInputNode()
        effect = SaturationPulse(
            input_node, intensity=0.6, base_saturation=0.3, signal=FrameSignal.freq_high
        )

        # Test that parameters are stored correctly
        assert effect.intensity == 0.6
        assert effect.base_saturation == 0.3
        assert effect.signal == FrameSignal.freq_high

    def test_parameter_bounds(self):
        """Test that parameters are within reasonable bounds"""
        input_node = MockInputNode()
        effect = SaturationPulse(
            input_node,
            intensity=2.0,  # High intensity
            base_saturation=1.5,  # High base
            signal=FrameSignal.sustained_high,
        )

        # Test that high values are accepted (clamping happens in _set_effect_uniforms)
        assert effect.intensity == 2.0
        assert effect.base_saturation == 1.5

    def test_generate_vibe(self):
        """Test generate method with vibe"""
        input_node = MockInputNode()
        effect = SaturationPulse(input_node)

        vibe = Vibe(mode=Mode.gentle)

        # Should not raise any exceptions
        effect.generate(vibe)
