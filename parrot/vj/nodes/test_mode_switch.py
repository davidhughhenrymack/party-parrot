#!/usr/bin/env python3

import pytest
import moderngl as mgl
from unittest.mock import Mock

from parrot.vj.nodes.mode_switch import ModeSwitch
from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.director.frame import Frame
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode


class TestModeSwitch:
    """Test cases for ModeSwitch node"""

    def test_initialization_with_all_modes(self):
        """Test ModeSwitch initialization with all mode nodes"""
        rave_node = Mock(spec=BaseInterpretationNode)
        blackout_node = Mock(spec=BaseInterpretationNode)
        gentle_node = Mock(spec=BaseInterpretationNode)

        switch = ModeSwitch(rave=rave_node, blackout=blackout_node, gentle=gentle_node)

        # Should have all mode nodes
        assert switch.mode_nodes[Mode.rave] == rave_node
        assert switch.mode_nodes[Mode.blackout] == blackout_node
        assert switch.mode_nodes[Mode.gentle] == gentle_node

        # Should start with first available mode node
        assert switch.current_child in [rave_node, blackout_node, gentle_node]

        # Should include only current child in all_inputs
        all_inputs = switch.all_inputs
        assert len(all_inputs) == 1
        assert switch.current_child in all_inputs

    def test_initialization_with_partial_modes(self):
        """Test ModeSwitch initialization with only some mode nodes"""
        rave_node = Mock(spec=BaseInterpretationNode)
        blackout_node = Mock(spec=BaseInterpretationNode)

        switch = ModeSwitch(rave=rave_node, blackout=blackout_node)

        # Should have only provided mode nodes
        assert switch.mode_nodes[Mode.rave] == rave_node
        assert switch.mode_nodes[Mode.blackout] == blackout_node
        assert Mode.gentle not in switch.mode_nodes

        # Should include only current child in all_inputs
        all_inputs = switch.all_inputs
        assert len(all_inputs) == 1
        assert switch.current_child in all_inputs

    def test_initialization_with_kwargs(self):
        """Test ModeSwitch initialization using kwargs for mode names"""
        rave_node = Mock(spec=BaseInterpretationNode)
        blackout_node = Mock(spec=BaseInterpretationNode)

        switch = ModeSwitch(rave=rave_node, blackout=blackout_node)

        assert switch.mode_nodes[Mode.rave] == rave_node
        assert switch.mode_nodes[Mode.blackout] == blackout_node

    def test_initialization_empty_raises_error(self):
        """Test that initialization with no nodes raises an error"""
        with pytest.raises(ValueError, match="At least one mode node must be provided"):
            ModeSwitch()

    def test_initialization_invalid_mode_raises_error(self):
        """Test that initialization with invalid mode name raises an error"""
        rave_node = Mock(spec=BaseInterpretationNode)

        with pytest.raises(ValueError, match="Unknown mode: invalid_mode"):
            ModeSwitch(rave=rave_node, invalid_mode=Mock())

    def test_enter_exit_lifecycle(self):
        """Test enter/exit lifecycle management"""
        rave_node = Mock(spec=BaseInterpretationNode)
        switch = ModeSwitch(rave=rave_node)
        context = Mock(spec=mgl.Context)

        # Test enter - should only call enter on current_child
        switch.enter(context)
        rave_node.enter.assert_called_once_with(context)
        assert switch._context == context

        # Test exit - should only call exit on current_child
        switch.exit()
        rave_node.exit.assert_called_once()
        assert switch._context is None

    def test_generate_switches_to_available_mode(self):
        """Test that generate switches to the correct mode when available"""
        rave_node = Mock(spec=BaseInterpretationNode)
        blackout_node = Mock(spec=BaseInterpretationNode)
        switch = ModeSwitch(rave=rave_node, blackout=blackout_node)

        # Test with rave mode - should use rave node
        rave_vibe = Vibe(Mode.rave)
        switch.generate(rave_vibe)
        assert switch.current_child == rave_node
        rave_node.generate.assert_called_once_with(rave_vibe)

        # Reset and test with blackout mode - should switch to blackout node
        rave_node.generate.reset_mock()
        blackout_vibe = Vibe(Mode.blackout)
        switch.generate(blackout_vibe)
        assert switch.current_child == blackout_node
        blackout_node.generate.assert_called_once_with(blackout_vibe)

    def test_generate_keeps_current_when_mode_unavailable(self):
        """Test that generate keeps current child when mode is not available"""
        rave_node = Mock(spec=BaseInterpretationNode)
        switch = ModeSwitch(rave=rave_node)  # Only rave mode available

        # Start with rave mode
        rave_vibe = Vibe(Mode.rave)
        switch.generate(rave_vibe)
        assert switch.current_child == rave_node

        # Try gentle mode (not available) - should keep rave node
        gentle_vibe = Vibe(Mode.gentle)
        switch.generate(gentle_vibe)
        assert switch.current_child == rave_node  # Should stay the same
        rave_node.generate.assert_called_with(
            gentle_vibe
        )  # But still generate with new vibe

    def test_render_current_child(self):
        """Test render uses current_child"""
        rave_node = Mock(spec=BaseInterpretationNode)
        switch = ModeSwitch(rave=rave_node)

        # Mock objects
        frame = Mock(spec=Frame)
        scheme = Mock(spec=ColorScheme)
        context = Mock(spec=mgl.Context)
        mock_framebuffer = Mock(spec=mgl.Framebuffer)

        # Mock child render
        rave_node.render = Mock(return_value=mock_framebuffer)

        # Set to rave mode (current_child should be rave node)
        switch.generate(Vibe(Mode.rave))

        # Render should use current_child
        result = switch.render(frame, scheme, context)
        assert result == mock_framebuffer
        rave_node.render.assert_called_once_with(frame, scheme, context)

    def test_mode_switching_between_available_modes(self):
        """Test switching between different available modes"""
        rave_node = Mock(spec=BaseInterpretationNode)
        blackout_node = Mock(spec=BaseInterpretationNode)
        gentle_node = Mock(spec=BaseInterpretationNode)
        switch = ModeSwitch(rave=rave_node, blackout=blackout_node, gentle=gentle_node)

        # Mock objects
        frame = Mock(spec=Frame)
        scheme = Mock(spec=ColorScheme)
        context = Mock(spec=mgl.Context)

        mock_rave_framebuffer = Mock(spec=mgl.Framebuffer)
        mock_blackout_framebuffer = Mock(spec=mgl.Framebuffer)
        mock_gentle_framebuffer = Mock(spec=mgl.Framebuffer)

        rave_node.render = Mock(return_value=mock_rave_framebuffer)
        blackout_node.render = Mock(return_value=mock_blackout_framebuffer)
        gentle_node.render = Mock(return_value=mock_gentle_framebuffer)

        # Start in rave mode
        switch.generate(Vibe(Mode.rave))
        assert switch.current_child == rave_node
        result = switch.render(frame, scheme, context)
        assert result == mock_rave_framebuffer

        # Switch to blackout
        switch.generate(Vibe(Mode.blackout))
        assert switch.current_child == blackout_node
        result = switch.render(frame, scheme, context)
        assert result == mock_blackout_framebuffer

        # Switch to gentle mode
        switch.generate(Vibe(Mode.gentle))
        assert switch.current_child == gentle_node
        result = switch.render(frame, scheme, context)
        assert result == mock_gentle_framebuffer

    def test_enter_exit_on_switch(self):
        """Test that enter/exit is called when switching children"""
        rave_node = Mock(spec=BaseInterpretationNode)
        blackout_node = Mock(spec=BaseInterpretationNode)
        switch = ModeSwitch(rave=rave_node, blackout=blackout_node)
        context = Mock(spec=mgl.Context)

        # Enter the switch (should enter current child)
        switch.enter(context)
        switch.current_child.enter.assert_called_once_with(context)

        # Determine which node was the initial current_child
        initial_child = switch.current_child
        other_child = blackout_node if initial_child == rave_node else rave_node
        other_mode = Mode.blackout if initial_child == rave_node else Mode.rave

        initial_child.enter.reset_mock()

        # Switch to the other mode (should exit current child and enter other child)
        switch.generate(Vibe(other_mode))
        initial_child.exit.assert_called_once()
        other_child.enter.assert_called_once_with(context)

        # Reset mocks
        initial_child.exit.reset_mock()
        other_child.enter.reset_mock()

        # Switch back (should exit other child and enter initial child)
        initial_mode = Mode.rave if initial_child == rave_node else Mode.blackout
        switch.generate(Vibe(initial_mode))
        other_child.exit.assert_called_once()
        initial_child.enter.assert_called_once_with(context)

    def test_no_enter_exit_when_mode_unavailable(self):
        """Test that no enter/exit happens when switching to unavailable mode"""
        rave_node = Mock(spec=BaseInterpretationNode)
        switch = ModeSwitch(rave=rave_node)  # Only rave available
        context = Mock(spec=mgl.Context)

        # Enter the switch
        switch.enter(context)
        rave_node.enter.assert_called_once_with(context)
        rave_node.enter.reset_mock()

        # Try to switch to unavailable mode - should not trigger enter/exit
        switch.generate(Vibe(Mode.blackout))
        rave_node.exit.assert_not_called()
        rave_node.enter.assert_not_called()
        assert switch.current_child == rave_node


if __name__ == "__main__":
    pytest.main([__file__])
