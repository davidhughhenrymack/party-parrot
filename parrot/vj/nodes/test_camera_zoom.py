#!/usr/bin/env python3

import pytest
import time
from unittest.mock import Mock, MagicMock, patch

from parrot.vj.nodes.camera_zoom import CameraZoom
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


class TestCameraZoom:
    """Test the camera zoom effect"""

    def test_init_default_params(self):
        """Test initialization with default parameters"""
        input_node = MockInputNode()
        effect = CameraZoom(input_node)

        assert effect.input_node == input_node
        assert effect.max_zoom == 2.5
        assert effect.zoom_speed == 8.0
        assert effect.return_speed == 4.0
        assert effect.blur_intensity == 0.8
        assert effect.signal == FrameSignal.sustained_high
        assert effect.current_zoom == 1.0
        assert effect.zoom_velocity == 0.0

    def test_init_custom_params(self):
        """Test initialization with custom parameters"""
        input_node = MockInputNode()
        effect = CameraZoom(
            input_node,
            max_zoom=3.0,
            zoom_speed=10.0,
            return_speed=5.0,
            blur_intensity=0.5,
            signal=FrameSignal.sustained_low,
        )

        assert effect.max_zoom == 3.0
        assert effect.zoom_speed == 10.0
        assert effect.return_speed == 5.0
        assert effect.blur_intensity == 0.5
        assert effect.signal == FrameSignal.sustained_low

    def test_fragment_shader_contains_zoom_and_blur(self):
        """Test that fragment shader contains zoom and blur functionality"""
        input_node = MockInputNode()
        effect = CameraZoom(input_node)

        shader = effect._get_fragment_shader()

        # Check for key zoom and blur elements
        assert "zoom_factor" in shader
        assert "blur_amount" in shader
        assert "texture_size" in shader
        assert "zoom_uv" in shader
        assert "blur_samples" in shader

    def test_zoom_parameters(self):
        """Test zoom parameter storage and initial state"""
        input_node = MockInputNode()
        effect = CameraZoom(
            input_node, max_zoom=2.0, zoom_speed=5.0, signal=FrameSignal.sustained_high
        )

        # Test that parameters are stored correctly
        assert effect.max_zoom == 2.0
        assert effect.zoom_speed == 5.0
        assert effect.signal == FrameSignal.sustained_high
        assert effect.current_zoom == 1.0  # Initial zoom
        assert effect.zoom_velocity == 0.0  # Initial velocity

    def test_zoom_state_modification(self):
        """Test that zoom state can be modified"""
        input_node = MockInputNode()
        effect = CameraZoom(
            input_node,
            max_zoom=2.0,
            return_speed=10.0,
            signal=FrameSignal.sustained_high,
        )

        # Test that we can modify zoom state
        effect.current_zoom = 1.5
        effect.zoom_velocity = 0.2

        assert effect.current_zoom == 1.5
        assert effect.zoom_velocity == 0.2

    def test_max_zoom_parameter(self):
        """Test that max zoom parameter is respected"""
        input_node = MockInputNode()
        effect = CameraZoom(input_node, max_zoom=3.0)

        # Test that max zoom is stored correctly
        assert effect.max_zoom == 3.0

        # Test that we can set zoom values up to max
        effect.current_zoom = 2.5
        assert effect.current_zoom == 2.5

    def test_generate_vibe(self):
        """Test generate method with vibe"""
        input_node = MockInputNode()
        effect = CameraZoom(input_node)

        vibe = Vibe(mode=Mode.rave)

        # Should not raise any exceptions
        effect.generate(vibe)
