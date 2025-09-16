#!/usr/bin/env python3

import pytest
import numpy as np
import moderngl as mgl
from unittest.mock import Mock, MagicMock

from parrot.vj.nodes.multiply_compose import MultiplyCompose
from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.director.frame import Frame
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode


class MockNode(BaseInterpretationNode):
    """Mock node for testing"""

    def __init__(self, color=(1.0, 1.0, 1.0)):
        super().__init__([])
        self.color = color
        self.framebuffer = None
        self.texture = None

    def enter(self, context):
        # Create a simple texture with solid color
        self.texture = context.texture((100, 100), 3)
        self.framebuffer = context.framebuffer(color_attachments=[self.texture])

        # Fill with solid color
        self.framebuffer.use()
        context.clear(*self.color)

    def exit(self):
        if self.texture:
            self.texture.release()
        if self.framebuffer:
            self.framebuffer.release()

    def generate(self, vibe):
        pass

    def render(self, frame, scheme, context):
        return self.framebuffer


def test_multiply_compose_initialization():
    """Test MultiplyCompose initialization"""
    base = MockNode(color=(1.0, 0.0, 0.0))  # Red
    mask = MockNode(color=(1.0, 1.0, 1.0))  # White

    compose = MultiplyCompose(base, mask)

    assert compose.base_layer == base
    assert compose.mask_layer == mask
    assert compose.width == 1280  # DEFAULT_WIDTH
    assert compose.height == 720  # DEFAULT_HEIGHT


def test_multiply_compose_gl_setup():
    """Test OpenGL resource setup"""
    # Create a mock OpenGL context
    ctx = Mock(spec=mgl.Context)
    mock_texture = Mock(spec=mgl.Texture)
    mock_framebuffer = Mock(spec=mgl.Framebuffer)
    mock_program = Mock(spec=mgl.Program)
    mock_vao = Mock(spec=mgl.VertexArray)
    mock_buffer = Mock()

    ctx.texture.return_value = mock_texture
    ctx.framebuffer.return_value = mock_framebuffer
    ctx.program.return_value = mock_program
    ctx.vertex_array.return_value = mock_vao
    ctx.buffer.return_value = mock_buffer

    base = MockNode()
    mask = MockNode()
    compose = MultiplyCompose(base, mask, width=100, height=100)

    compose.enter(ctx)

    # Verify GL resources were created
    ctx.texture.assert_called_with((100, 100), 3)
    ctx.framebuffer.assert_called_with(color_attachments=[mock_texture])
    assert ctx.program.called
    assert ctx.vertex_array.called


def test_multiply_compose_render_logic():
    """Test the multiplicative composition logic conceptually"""
    base = MockNode(color=(0.5, 0.8, 0.2))  # Some video color
    mask = MockNode(color=(1.0, 1.0, 1.0))  # White mask (should show full video)

    compose = MultiplyCompose(base, mask, width=100, height=100)

    # The actual multiplication happens in the shader, but we can verify
    # that the composition node is set up correctly
    assert compose.base_layer == base
    assert compose.mask_layer == mask

    # Test with black mask (should hide video)
    black_mask = MockNode(color=(0.0, 0.0, 0.0))
    compose_hidden = MultiplyCompose(base, black_mask, width=100, height=100)

    assert compose_hidden.mask_layer == black_mask


def test_multiply_compose_cleanup():
    """Test resource cleanup"""
    ctx = Mock(spec=mgl.Context)
    mock_texture = Mock(spec=mgl.Texture)
    mock_framebuffer = Mock(spec=mgl.Framebuffer)
    mock_program = Mock(spec=mgl.Program)
    mock_vao = Mock(spec=mgl.VertexArray)
    mock_buffer = Mock()

    ctx.texture.return_value = mock_texture
    ctx.framebuffer.return_value = mock_framebuffer
    ctx.program.return_value = mock_program
    ctx.vertex_array.return_value = mock_vao
    ctx.buffer.return_value = mock_buffer

    base = MockNode()
    mask = MockNode()
    compose = MultiplyCompose(base, mask)

    compose.enter(ctx)
    compose.exit()

    # Verify resources were released
    mock_texture.release.assert_called()
    mock_framebuffer.release.assert_called()
    mock_program.release.assert_called()
    mock_vao.release.assert_called()


def test_multiply_compose_with_missing_layers():
    """Test behavior when one layer is missing"""
    base = MockNode()
    mask = MockNode()
    compose = MultiplyCompose(base, mask)

    # Mock the render method to return None for one layer
    base.render = Mock(return_value=None)
    mask.render = Mock(return_value=Mock())

    ctx = Mock(spec=mgl.Context)
    frame = Mock(spec=Frame)
    scheme = Mock(spec=ColorScheme)

    # Set up minimal GL resources
    compose.framebuffer = Mock(spec=mgl.Framebuffer)

    result = compose.render(frame, scheme, ctx)

    # Should return the compose framebuffer (cleared to black)
    assert result == compose.framebuffer
    compose.framebuffer.use.assert_called()
    ctx.clear.assert_called_with(0.0, 0.0, 0.0)


if __name__ == "__main__":
    pytest.main([__file__])
