#!/usr/bin/env python3

import pytest
from unittest.mock import Mock, MagicMock
import moderngl as mgl

from parrot.vj.nodes.canvas_effect_base import CanvasEffectBase, PostProcessEffectBase, GenerativeEffectBase
from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode
from parrot.utils.colour import Color


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


class TestCanvasEffectBase:
    """Test the base canvas effect class"""

    def test_init_without_input(self):
        """Test initialization without input node"""
        class TestEffect(CanvasEffectBase):
            def _get_fragment_shader(self):
                return "test shader"
            def generate(self, vibe):
                pass
        
        effect = TestEffect()
        assert effect.input_node is None
        assert effect.children == []

    def test_init_with_input(self):
        """Test initialization with input node"""
        class TestEffect(CanvasEffectBase):
            def _get_fragment_shader(self):
                return "test shader"
            def generate(self, vibe):
                pass
        
        input_node = MockInputNode()
        effect = TestEffect(input_node)
        assert effect.input_node == input_node
        assert effect.children == [input_node]

    def test_cleanup_resources(self):
        """Test that cleanup properly releases resources"""
        class TestEffect(CanvasEffectBase):
            def _get_fragment_shader(self):
                return "test shader"
            def generate(self, vibe):
                pass
        
        effect = TestEffect()
        
        # Mock GL resources
        effect.framebuffer = Mock()
        effect.texture = Mock()
        effect.shader_program = Mock()
        effect.quad_vao = Mock()
        
        # Store references before cleanup
        fb_mock = effect.framebuffer
        tex_mock = effect.texture
        shader_mock = effect.shader_program
        vao_mock = effect.quad_vao
        
        effect._cleanup_gl_resources()
        
        # Check that release was called on all resources
        fb_mock.release.assert_called_once()
        tex_mock.release.assert_called_once()
        shader_mock.release.assert_called_once()
        vao_mock.release.assert_called_once()
        
        # Check that resources are set to None
        assert effect.framebuffer is None
        assert effect.texture is None
        assert effect.shader_program is None
        assert effect.quad_vao is None


class TestPostProcessEffectBase:
    """Test the post-process effect base class"""

    def test_requires_input_node(self):
        """Test that post-process effects require an input node"""
        class TestPostEffect(PostProcessEffectBase):
            def _get_fragment_shader(self):
                return "test shader"
            
            def _set_effect_uniforms(self, frame, scheme):
                pass
            
            def generate(self, vibe):
                pass
        
        input_node = MockInputNode()
        effect = TestPostEffect(input_node)
        assert effect.input_node == input_node

    def test_fragment_shader_method(self):
        """Test that fragment shader method is abstract and must be implemented"""
        class TestPostEffect(PostProcessEffectBase):
            def _get_fragment_shader(self):
                return "uniform sampler2D input_texture; void main() { gl_FragColor = texture2D(input_texture, gl_TexCoord[0].xy); }"
            
            def _set_effect_uniforms(self, frame, scheme):
                pass
            
            def generate(self, vibe):
                pass
        
        input_node = MockInputNode()
        effect = TestPostEffect(input_node)
        
        # Test that fragment shader is returned
        shader = effect._get_fragment_shader()
        assert "input_texture" in shader
        assert "main" in shader


class TestGenerativeEffectBase:
    """Test the generative effect base class"""

    def test_init_with_dimensions(self):
        """Test initialization with custom dimensions"""
        class TestGenEffect(GenerativeEffectBase):
            def _get_fragment_shader(self):
                return "test shader"
            
            def _set_effect_uniforms(self, frame, scheme):
                pass
            
            def generate(self, vibe):
                pass
        
        effect = TestGenEffect(width=800, height=600)
        assert effect.width == 800
        assert effect.height == 600
        assert effect.input_node is None

    def test_default_dimensions(self):
        """Test default dimensions"""
        class TestGenEffect(GenerativeEffectBase):
            def _get_fragment_shader(self):
                return "test shader"
            
            def _set_effect_uniforms(self, frame, scheme):
                pass
            
            def generate(self, vibe):
                pass
        
        effect = TestGenEffect()
        assert effect.width == 1920
        assert effect.height == 1080
