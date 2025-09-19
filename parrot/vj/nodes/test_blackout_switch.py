#!/usr/bin/env python3

import pytest
import moderngl as mgl
from unittest.mock import Mock

from parrot.vj.nodes.blackout_switch import BlackoutSwitch
from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.director.frame import Frame
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode


class TestBlackoutSwitch:
    """Test cases for BlackoutSwitch node"""

    def test_initialization(self):
        """Test BlackoutSwitch initialization"""
        # Create a mock child node
        child = Mock(spec=BaseInterpretationNode)

        switch = BlackoutSwitch(child)

        # Should have child and black node
        assert switch.child == child
        assert switch.black_node is not None
        assert switch.current_child == child  # Should start with main child

        # Should include both child and black node in all_inputs
        all_inputs = switch.all_inputs
        assert len(all_inputs) == 2
        assert switch.child in all_inputs
        assert switch.black_node in all_inputs

    def test_enter_exit_lifecycle(self):
        """Test enter/exit lifecycle management"""
        child = Mock(spec=BaseInterpretationNode)
        switch = BlackoutSwitch(child)
        context = Mock(spec=mgl.Context)

        # Test enter - should only call enter on current_child (which starts as main child)
        switch.enter(context)
        child.enter.assert_called_once_with(context)
        assert switch._context == context

        # Test exit - should only call exit on current_child
        switch.exit()
        child.exit.assert_called_once()
        assert switch._context is None

    def test_generate_switches_current_child(self):
        """Test that generate switches current_child based on mode"""
        child = Mock(spec=BaseInterpretationNode)
        switch = BlackoutSwitch(child)

        # Mock the black node's generate method
        switch.black_node.generate = Mock()

        # Test with rave mode - should use main child
        rave_vibe = Vibe(Mode.rave)
        switch.generate(rave_vibe)
        assert switch.current_child == child
        child.generate.assert_called_once_with(rave_vibe)

        # Reset and test with blackout mode - should switch to black node
        child.generate.reset_mock()
        blackout_vibe = Vibe(Mode.blackout)
        switch.generate(blackout_vibe)
        assert switch.current_child == switch.black_node
        switch.black_node.generate.assert_called_once_with(blackout_vibe)

    def test_render_current_child(self):
        """Test render uses current_child"""
        child = Mock(spec=BaseInterpretationNode)
        switch = BlackoutSwitch(child)

        # Mock objects
        frame = Mock(spec=Frame)
        scheme = Mock(spec=ColorScheme)
        context = Mock(spec=mgl.Context)
        mock_framebuffer = Mock(spec=mgl.Framebuffer)

        # Mock child render
        child.render = Mock(return_value=mock_framebuffer)

        # Set to rave mode (current_child should be main child)
        switch.generate(Vibe(Mode.rave))

        # Render should use current_child
        result = switch.render(frame, scheme, context)
        assert result == mock_framebuffer
        child.render.assert_called_once_with(frame, scheme, context)

    def test_render_blackout_mode(self):
        """Test render in blackout mode uses black node as current_child"""
        child = Mock(spec=BaseInterpretationNode)
        switch = BlackoutSwitch(child)

        # Mock objects
        frame = Mock(spec=Frame)
        scheme = Mock(spec=ColorScheme)
        context = Mock(spec=mgl.Context)
        mock_black_framebuffer = Mock(spec=mgl.Framebuffer)

        # Mock black node render
        switch.black_node.render = Mock(return_value=mock_black_framebuffer)
        child.render = Mock()

        # Set to blackout mode (current_child should switch to black_node)
        switch.generate(Vibe(Mode.blackout))
        assert switch.current_child == switch.black_node

        # Render should use current_child (which is now black_node)
        result = switch.render(frame, scheme, context)
        assert result == mock_black_framebuffer
        switch.black_node.render.assert_called_once_with(frame, scheme, context)
        child.render.assert_not_called()

    def test_mode_switching(self):
        """Test switching between modes and current_child changes"""
        child = Mock(spec=BaseInterpretationNode)
        switch = BlackoutSwitch(child)

        # Mock objects
        frame = Mock(spec=Frame)
        scheme = Mock(spec=ColorScheme)
        context = Mock(spec=mgl.Context)

        mock_child_framebuffer = Mock(spec=mgl.Framebuffer)
        mock_black_framebuffer = Mock(spec=mgl.Framebuffer)

        child.render = Mock(return_value=mock_child_framebuffer)
        switch.black_node.render = Mock(return_value=mock_black_framebuffer)

        # Start in rave mode
        switch.generate(Vibe(Mode.rave))
        assert switch.current_child == child
        result = switch.render(frame, scheme, context)
        assert result == mock_child_framebuffer

        # Switch to blackout
        switch.generate(Vibe(Mode.blackout))
        assert switch.current_child == switch.black_node
        result = switch.render(frame, scheme, context)
        assert result == mock_black_framebuffer

        # Switch back to gentle mode
        switch.generate(Vibe(Mode.gentle))
        assert switch.current_child == child
        result = switch.render(frame, scheme, context)
        assert result == mock_child_framebuffer

    def test_enter_exit_on_switch(self):
        """Test that enter/exit is called when switching children"""
        child = Mock(spec=BaseInterpretationNode)
        switch = BlackoutSwitch(child)
        context = Mock(spec=mgl.Context)

        # Mock the black node's enter/exit methods
        switch.black_node.enter = Mock()
        switch.black_node.exit = Mock()
        switch.black_node.generate = Mock()

        # Enter the switch (should enter main child)
        switch.enter(context)
        child.enter.assert_called_once_with(context)
        child.enter.reset_mock()

        # Switch to blackout mode (should exit main child and enter black node)
        switch.generate(Vibe(Mode.blackout))
        child.exit.assert_called_once()
        switch.black_node.enter.assert_called_once_with(context)

        # Reset mocks
        child.exit.reset_mock()
        switch.black_node.enter.reset_mock()

        # Switch back to rave mode (should exit black node and enter main child)
        switch.generate(Vibe(Mode.rave))
        switch.black_node.exit.assert_called_once()
        child.enter.assert_called_once_with(context)


if __name__ == "__main__":
    pytest.main([__file__])
