#!/usr/bin/env python3

import pytest
import moderngl as mgl
import numpy as np
from unittest.mock import Mock

from parrot.vj.nodes.infinite_zoom_effect import InfiniteZoomEffect
from parrot.vj.nodes.black import Black
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode
from parrot.graph.BaseInterpretationNode import Vibe
from parrot.utils.colour import Color


class TestInfiniteZoomEffect:
    """Test the InfiniteZoomEffect node"""

    def test_init(self):
        """Test InfiniteZoomEffect initialization"""
        input_node = Black()
        effect = InfiniteZoomEffect(input_node)

        assert effect.input_node == input_node
        assert effect.zoom_speed == 1.5
        assert effect.num_layers == 4
        assert effect.layer_scale_factor == 0.7
        assert effect.rotation_speed == 0.3
        assert effect.signal == FrameSignal.freq_low

    def test_init_with_params(self):
        """Test InfiniteZoomEffect initialization with custom parameters"""
        input_node = Black()
        effect = InfiniteZoomEffect(
            input_node,
            zoom_speed=2.0,
            num_layers=6,
            layer_scale_factor=0.8,
            rotation_speed=0.5,
            signal=FrameSignal.freq_high,
        )

        assert effect.zoom_speed == 2.0
        assert effect.num_layers == 6
        assert effect.layer_scale_factor == 0.8
        assert effect.rotation_speed == 0.5
        assert effect.signal == FrameSignal.freq_high

    def test_parameter_clamping(self):
        """Test that parameters are clamped to valid ranges"""
        input_node = Black()
        effect = InfiniteZoomEffect(
            input_node,
            num_layers=20,  # Should be clamped to 8
            layer_scale_factor=1.5,  # Should be clamped to 0.95
        )

        assert effect.num_layers == 8
        assert effect.layer_scale_factor == 0.95

        # Test lower bounds
        effect2 = InfiniteZoomEffect(
            input_node,
            num_layers=1,  # Should be clamped to 2
            layer_scale_factor=0.1,  # Should be clamped to 0.3
        )

        assert effect2.num_layers == 2
        assert effect2.layer_scale_factor == 0.3

    def test_generate(self):
        """Test generate method randomizes parameters"""
        input_node = Black()
        effect = InfiniteZoomEffect(input_node)

        # Store original values
        original_zoom_speed = effect.zoom_speed
        original_num_layers = effect.num_layers
        original_layer_scale_factor = effect.layer_scale_factor
        original_rotation_speed = effect.rotation_speed
        original_signal = effect.signal

        # Generate new parameters
        vibe = Vibe(mode=Mode.rave)
        effect.generate(vibe)

        # At least some parameters should change (though randomness means they might not)
        # Just check that the values are within expected ranges
        assert 0.5 <= effect.zoom_speed <= 3.0
        assert 2 <= effect.num_layers <= 6
        assert 0.5 <= effect.layer_scale_factor <= 0.85
        assert -0.8 <= effect.rotation_speed <= 0.8
        assert effect.signal in [
            FrameSignal.freq_all,
            FrameSignal.freq_high,
            FrameSignal.freq_low,
            FrameSignal.sustained_low,
            FrameSignal.sustained_high,
            FrameSignal.strobe,
            FrameSignal.big_blinder,
            FrameSignal.small_blinder,
            FrameSignal.pulse,
            FrameSignal.dampen,
        ]

    def test_fragment_shader(self):
        """Test that fragment shader is valid GLSL"""
        input_node = Black()
        effect = InfiniteZoomEffect(input_node)

        shader_source = effect._get_fragment_shader()

        # Basic checks for GLSL structure
        assert "#version 330 core" in shader_source
        assert "in vec2 uv;" in shader_source
        assert "out vec3 color;" in shader_source
        assert "uniform sampler2D input_texture;" in shader_source
        assert "void main()" in shader_source

        # Check for key uniforms
        assert "uniform float zoom_offset;" in shader_source
        assert "uniform float rotation_offset;" in shader_source
        assert "uniform int num_layers;" in shader_source
        assert "uniform float layer_scale_factor;" in shader_source
        assert "uniform float signal_intensity;" in shader_source

    @pytest.mark.skip(
        reason="Requires OpenGL context - run manually for integration testing"
    )
    def test_render_headless(self):
        """Test rendering with headless OpenGL context"""
        # This test requires a proper OpenGL context setup
        # Skip by default but can be run manually for integration testing

        # Create headless context
        ctx = mgl.create_context(standalone=True, require=330)

        # Create input node and effect
        input_node = Black()
        effect = InfiniteZoomEffect(input_node)

        # Enter nodes
        input_node.enter(ctx)
        effect.enter(ctx)

        # Create test frame and scheme
        frame = Frame({FrameSignal.freq_low: 0.5})
        scheme = ColorScheme(Color("red"), Color("blue"), Color("white"))

        # Generate and render
        vibe = Vibe(mode=Mode.rave)
        input_node.generate(vibe)
        effect.generate(vibe)

        result = effect.render(frame, scheme, ctx)

        # Check result
        assert result is not None
        assert isinstance(result, mgl.Framebuffer)
        assert result.width > 0
        assert result.height > 0

        # Cleanup
        effect.exit()
        input_node.exit()
        ctx.release()

    def test_animation_state_updates(self):
        """Test that animation state updates correctly"""
        input_node = Black()
        effect = InfiniteZoomEffect(input_node, zoom_speed=1.0, rotation_speed=1.0)

        # Create real frame and scheme objects
        frame = Frame({FrameSignal.freq_low: 0.5})
        scheme = ColorScheme(Color("red"), Color("blue"), Color("white"))

        # Mock shader program with dictionary-like behavior
        shader_mock = Mock()
        shader_mock.__setitem__ = Mock()  # Allow item assignment
        effect.shader_program = shader_mock
        effect.framebuffer = Mock()
        effect.framebuffer.width = 1920
        effect.framebuffer.height = 1080

        # Call _set_effect_uniforms multiple times to test animation
        import time

        start_time = time.time()
        effect.last_time = start_time

        # First call
        effect._set_effect_uniforms(frame, scheme)
        first_zoom_offset = effect.zoom_offset
        first_rotation_offset = effect.rotation_offset

        # Simulate time passing
        effect.last_time = start_time + 0.1  # 100ms later

        # Second call
        effect._set_effect_uniforms(frame, scheme)
        second_zoom_offset = effect.zoom_offset
        second_rotation_offset = effect.rotation_offset

        # Animation should have progressed
        assert second_zoom_offset != first_zoom_offset
        assert second_rotation_offset != first_rotation_offset

        # Zoom offset should wrap around at 1.0
        effect.zoom_offset = 0.9
        effect.zoom_speed = 2.0
        effect.last_time = start_time + 0.2
        effect._set_effect_uniforms(frame, scheme)

        # Should have wrapped around
        assert 0.0 <= effect.zoom_offset < 1.0

    def test_shader_uniform_validation(self):
        """Test that all uniforms set in _set_effect_uniforms exist in the shader"""
        input_node = Black()
        effect = InfiniteZoomEffect(input_node)

        # Get shader source and extract uniform declarations
        shader_source = effect._get_fragment_shader()

        # Parse uniforms from shader source
        declared_uniforms = set()
        for line in shader_source.split("\n"):
            line = line.strip()
            if line.startswith("uniform "):
                # Extract uniform name: "uniform float zoom_offset;" -> "zoom_offset"
                parts = line.split()
                if len(parts) >= 3:
                    uniform_name = parts[2].rstrip(";")
                    declared_uniforms.add(uniform_name)

        # Expected uniforms that should be set by _set_effect_uniforms
        expected_uniforms = {
            "zoom_offset",
            "rotation_offset",
            "num_layers",
            "layer_scale_factor",
            "signal_intensity",
        }

        # All expected uniforms should be declared in shader
        missing_uniforms = expected_uniforms - declared_uniforms
        assert (
            not missing_uniforms
        ), f"Uniforms set in code but not declared in shader: {missing_uniforms}"

        # No extra uniforms should be declared but not set
        # (This is a warning, not an error, as some uniforms might be set elsewhere)
        extra_uniforms = (
            declared_uniforms - expected_uniforms - {"input_texture"}
        )  # input_texture is set in base class
        if extra_uniforms:
            print(
                f"Warning: Uniforms declared in shader but not set in _set_effect_uniforms: {extra_uniforms}"
            )

    def test_safe_uniform_setting(self):
        """Test the safe uniform setting functionality"""
        input_node = Black()
        effect = InfiniteZoomEffect(input_node)

        # Mock shader program that raises KeyError for non-existent uniforms
        shader_mock = Mock()

        def mock_getitem(self, key):
            if key in [
                "zoom_offset",
                "rotation_offset",
                "num_layers",
                "layer_scale_factor",
                "signal_intensity",
            ]:
                return Mock()  # Simulate existing uniform
            else:
                raise KeyError(f"Uniform '{key}' not found")

        def mock_setitem(self, key, value):
            if key not in [
                "zoom_offset",
                "rotation_offset",
                "num_layers",
                "layer_scale_factor",
                "signal_intensity",
            ]:
                raise KeyError(f"Uniform '{key}' not found")

        shader_mock.__getitem__ = mock_getitem
        shader_mock.__setitem__ = mock_setitem
        effect.shader_program = shader_mock

        # Test safe setting of existing uniform
        result = effect._safe_set_uniform("zoom_offset", 0.5)
        assert result is True

        # Test safe setting of non-existent uniform
        result = effect._safe_set_uniform("non_existent_uniform", 0.5)
        assert result is False

        # Test with no shader program
        effect.shader_program = None
        result = effect._safe_set_uniform("zoom_offset", 0.5)
        assert result is False
