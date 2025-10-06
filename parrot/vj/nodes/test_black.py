#!/usr/bin/env python3

import pytest
from unittest.mock import Mock, MagicMock, patch
from beartype import beartype

from parrot.vj.nodes.black import Black
from parrot.director.frame import Frame
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode
from parrot.graph.BaseInterpretationNode import Vibe


@beartype
class TestBlack:
    """Test cases for Black node"""

    def test_init(self):
        """Test Black node initialization"""
        black = Black()
        assert black.children == []
        assert black.framebuffer is None

    def test_enter_exit(self):
        """Test enter and exit lifecycle"""
        black = Black()

        # Test that framebuffer starts as None
        assert black.framebuffer is None

        # Test exit with no resources (should not crash)
        black.exit()
        assert black.framebuffer is None

        # Test exit with mock framebuffer
        mock_framebuffer = Mock()
        black.framebuffer = mock_framebuffer
        black.exit()
        mock_framebuffer.release.assert_called_once()
        assert black.framebuffer is None

    def test_generate(self):
        """Test generate method"""
        black = Black()
        vibe = Vibe(Mode.chill)

        # Generate should not raise any errors
        black.generate(vibe)

    def test_render_logic(self):
        """Test render method logic without mocking GL context"""
        black = Black()

        # Test that framebuffer is initially None
        assert black.framebuffer is None

        # Test that setting a framebuffer works
        mock_framebuffer = Mock()
        black.framebuffer = mock_framebuffer
        assert black.framebuffer == mock_framebuffer
