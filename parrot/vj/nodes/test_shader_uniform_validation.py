#!/usr/bin/env python3

import pytest
import moderngl as mgl
from unittest.mock import Mock
from typing import Set, Type
import inspect

from parrot.vj.nodes.canvas_effect_base import CanvasEffectBase, PostProcessEffectBase
from parrot.vj.nodes.infinite_zoom_effect import InfiniteZoomEffect
from parrot.vj.nodes.pixelate_effect import PixelateEffect
from parrot.vj.nodes.rgb_shift_effect import RGBShiftEffect
from parrot.vj.nodes.datamosh_effect import DatamoshEffect
from parrot.vj.nodes.noise_effect import NoiseEffect
from parrot.vj.nodes.scanlines_effect import ScanlinesEffect
from parrot.vj.nodes.black import Black
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.utils.colour import Color


def extract_shader_uniforms(shader_source: str) -> Set[str]:
    """Extract uniform names from GLSL shader source code"""
    uniforms = set()
    for line in shader_source.split("\n"):
        line = line.strip()
        if line.startswith("uniform "):
            # Extract uniform name: "uniform float zoom_offset;" -> "zoom_offset"
            parts = line.split()
            if len(parts) >= 3:
                uniform_name = parts[2].rstrip(";")
                uniforms.add(uniform_name)
    return uniforms


def get_uniforms_set_by_method(effect_instance, frame, scheme) -> Set[str]:
    """Get the set of uniforms that would be set by _set_effect_uniforms"""
    # Mock shader program to capture uniform assignments
    uniforms_set = set()

    def mock_setitem(self, key, value):
        uniforms_set.add(key)

    shader_mock = Mock()
    shader_mock.__setitem__ = mock_setitem

    # Mock framebuffer for effects that use it
    framebuffer_mock = Mock()
    framebuffer_mock.width = 1920
    framebuffer_mock.height = 1080

    # Store original values
    original_shader = effect_instance.shader_program
    original_framebuffer = effect_instance.framebuffer

    try:
        effect_instance.shader_program = shader_mock
        effect_instance.framebuffer = framebuffer_mock

        # Call the method to see what uniforms it tries to set
        effect_instance._set_effect_uniforms(frame, scheme)

    finally:
        # Restore original values
        effect_instance.shader_program = original_shader
        effect_instance.framebuffer = original_framebuffer

    return uniforms_set


class TestShaderUniformValidation:
    """Test shader uniform validation for all canvas effects"""

    def setup_method(self):
        """Setup test fixtures"""
        self.frame = Frame({FrameSignal.freq_low: 0.5, FrameSignal.freq_high: 0.3})
        self.scheme = ColorScheme(Color("red"), Color("blue"), Color("white"))
        self.input_node = Black()

    @pytest.mark.parametrize(
        "effect_class",
        [
            InfiniteZoomEffect,
            PixelateEffect,
            RGBShiftEffect,
            DatamoshEffect,
            NoiseEffect,
            ScanlinesEffect,
        ],
    )
    def test_shader_uniform_consistency(
        self, effect_class: Type[PostProcessEffectBase]
    ):
        """Test that all uniforms set in _set_effect_uniforms exist in the shader"""
        # Create effect instance
        if issubclass(effect_class, PostProcessEffectBase):
            effect = effect_class(self.input_node)
        else:
            effect = effect_class()

        # Get shader source and extract declared uniforms
        shader_source = effect._get_fragment_shader()
        declared_uniforms = extract_shader_uniforms(shader_source)

        # Get uniforms that the code tries to set
        uniforms_set = get_uniforms_set_by_method(effect, self.frame, self.scheme)

        # Filter out uniforms set by base class (these are handled separately)
        base_uniforms = {"input_texture"}
        code_uniforms = uniforms_set - base_uniforms

        # All uniforms set in code should be declared in shader
        missing_uniforms = code_uniforms - declared_uniforms
        assert not missing_uniforms, (
            f"{effect_class.__name__}: Uniforms set in code but not declared in shader: {missing_uniforms}\n"
            f"Declared uniforms: {declared_uniforms}\n"
            f"Code uniforms: {code_uniforms}"
        )

        # Warn about unused uniforms (declared but not set)
        unused_uniforms = declared_uniforms - code_uniforms - base_uniforms
        if unused_uniforms:
            print(
                f"Warning: {effect_class.__name__} has unused uniforms: {unused_uniforms}"
            )

    def test_safe_uniform_setting_base_class(self):
        """Test the _safe_set_uniform method in the base class"""
        effect = InfiniteZoomEffect(self.input_node)

        # Test with no shader program
        assert effect._safe_set_uniform("test_uniform", 0.5) is False

        # Mock shader program with some uniforms
        shader_mock = Mock()
        existing_uniforms = {"zoom_offset", "rotation_offset"}

        def mock_getitem(self, key):
            if key in existing_uniforms:
                return Mock()
            else:
                raise KeyError(f"Uniform '{key}' not found")

        def mock_setitem(self, key, value):
            if key not in existing_uniforms:
                raise KeyError(f"Uniform '{key}' not found")

        shader_mock.__getitem__ = mock_getitem
        shader_mock.__setitem__ = mock_setitem
        effect.shader_program = shader_mock

        # Test setting existing uniform
        assert effect._safe_set_uniform("zoom_offset", 0.5) is True

        # Test setting non-existent uniform
        assert effect._safe_set_uniform("non_existent", 0.5) is False

    def test_shader_compilation_validation(self):
        """Test that all effect shaders can be compiled (requires OpenGL context)"""
        # This test is more comprehensive but requires OpenGL context
        # Skip by default but useful for integration testing
        pytest.skip("Requires OpenGL context - run manually for integration testing")

        # Create headless context
        ctx = mgl.create_context(standalone=True, require=330)

        effect_classes = [
            InfiniteZoomEffect,
            PixelateEffect,
            RGBShiftEffect,
            DatamoshEffect,
            NoiseEffect,
            ScanlinesEffect,
        ]

        for effect_class in effect_classes:
            try:
                # Create effect
                if issubclass(effect_class, PostProcessEffectBase):
                    effect = effect_class(self.input_node)
                else:
                    effect = effect_class()

                # Try to compile shader
                vertex_shader = effect._get_vertex_shader()
                fragment_shader = effect._get_fragment_shader()

                program = ctx.program(
                    vertex_shader=vertex_shader, fragment_shader=fragment_shader
                )

                # If we get here, compilation succeeded
                program.release()

            except Exception as e:
                pytest.fail(f"{effect_class.__name__} shader compilation failed: {e}")

        ctx.release()

    def test_uniform_type_consistency(self):
        """Test that uniform types in shader match the values being set"""
        effect = InfiniteZoomEffect(self.input_node)
        shader_source = effect._get_fragment_shader()

        # Parse uniform declarations with types
        uniform_types = {}
        for line in shader_source.split("\n"):
            line = line.strip()
            if line.startswith("uniform "):
                parts = line.split()
                if len(parts) >= 3:
                    uniform_type = parts[1]
                    uniform_name = parts[2].rstrip(";")
                    uniform_types[uniform_name] = uniform_type

        # Check that the types match expected values
        expected_types = {
            "zoom_offset": "float",
            "rotation_offset": "float",
            "num_layers": "int",
            "layer_scale_factor": "float",
            "signal_intensity": "float",
        }

        for uniform_name, expected_type in expected_types.items():
            if uniform_name in uniform_types:
                actual_type = uniform_types[uniform_name]
                assert actual_type == expected_type, (
                    f"Uniform '{uniform_name}' has type '{actual_type}' in shader "
                    f"but expected '{expected_type}'"
                )
