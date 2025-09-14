#!/usr/bin/env python3

import pytest
from unittest.mock import Mock, MagicMock, patch
from beartype import beartype

from parrot.vj.nodes.layer_compose import LayerCompose
from parrot.graph.BaseInterpretationNode import BaseInterpretationNode
from parrot.director.frame import Frame
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode
from parrot.graph.BaseInterpretationNode import Vibe


@beartype
class MockLayer(BaseInterpretationNode):
    """Mock layer for testing"""

    def __init__(self, name: str):
        super().__init__([])
        self.name = name
        self.entered = False
        self.exited = False
        self.generated = False

    def enter(self, context):
        self.entered = True

    def exit(self):
        self.exited = True

    def generate(self, vibe: Vibe):
        self.generated = True

    def render(self, frame: Frame, scheme: ColorScheme, context):
        mock_framebuffer = Mock()
        mock_framebuffer.color_attachments = [Mock()]
        return mock_framebuffer


@beartype
class TestLayerCompose:
    """Test cases for LayerCompose node"""

    def test_init(self):
        """Test LayerCompose initialization"""
        layer1 = MockLayer("layer1")
        layer2 = MockLayer("layer2")

        compose = LayerCompose(layer1, layer2)

        assert compose.children == [layer1, layer2]
        assert compose.layers == [layer1, layer2]
        assert compose.framebuffer is None
        assert compose.texture is None

    def test_init_empty(self):
        """Test LayerCompose with no layers"""
        compose = LayerCompose()

        assert compose.children == []
        assert compose.layers == []

    def test_enter_exit_lifecycle(self):
        """Test enter and exit clean up resources"""
        compose = LayerCompose()

        # Test that resources start as None
        assert compose.framebuffer is None
        assert compose.texture is None
        assert compose.shader_program is None
        assert compose.quad_vao is None

        # Test exit with no resources (should not crash)
        compose.exit()

        # Test exit with mock resources
        mock_framebuffer = Mock()
        mock_texture = Mock()
        mock_shader_program = Mock()
        mock_quad_vao = Mock()

        compose.framebuffer = mock_framebuffer
        compose.texture = mock_texture
        compose.shader_program = mock_shader_program
        compose.quad_vao = mock_quad_vao

        # Exit should clean up resources
        compose.exit()

        mock_framebuffer.release.assert_called_once()
        mock_texture.release.assert_called_once()
        mock_shader_program.release.assert_called_once()
        mock_quad_vao.release.assert_called_once()

        assert compose.framebuffer is None
        assert compose.texture is None
        assert compose.shader_program is None
        assert compose.quad_vao is None

    def test_generate(self):
        """Test generate method"""
        compose = LayerCompose()
        vibe = Vibe(Mode.gentle)

        # Generate should not raise errors
        compose.generate(vibe)

    def test_render_logic(self):
        """Test render method logic without mocking GL context"""
        compose = LayerCompose()

        # Test that GL resources are initially None
        assert compose.framebuffer is None
        assert compose.texture is None
        assert compose.shader_program is None
        assert compose.quad_vao is None

        # Test that setting resources works
        mock_framebuffer = Mock()
        compose.framebuffer = mock_framebuffer
        assert compose.framebuffer == mock_framebuffer

    def test_layer_count_logic(self):
        """Test layer counting and access logic"""
        layer1 = MockLayer("layer1")
        layer2 = MockLayer("layer2")
        compose = LayerCompose(layer1, layer2)

        # Test layer count
        assert len(compose.layers) == 2
        assert compose.layers[0] == layer1
        assert compose.layers[1] == layer2

    def test_children_handled_by_base_class(self):
        """Test that children are properly passed to base class for recursive handling"""
        layer1 = MockLayer("layer1")
        layer2 = MockLayer("layer2")

        compose = LayerCompose(layer1, layer2)

        # Verify children are set correctly for base class recursive methods
        assert compose.all_inputs == [layer1, layer2]
        assert compose.children == [layer1, layer2]
