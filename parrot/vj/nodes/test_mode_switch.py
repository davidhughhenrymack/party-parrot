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
        chill_node = Mock(spec=BaseInterpretationNode)

        switch = ModeSwitch(
            rave=rave_node, blackout=blackout_node, gentle=gentle_node, chill=chill_node
        )

        # Should have all mode nodes
        assert switch.mode_nodes[Mode.rave] == rave_node
        assert switch.mode_nodes[Mode.blackout] == blackout_node
        assert switch.mode_nodes[Mode.gentle] == gentle_node
        assert switch.mode_nodes[Mode.chill] == chill_node

        # Should start with first available mode node
        assert switch.current_child in [
            rave_node,
            blackout_node,
            gentle_node,
            chill_node,
        ]

        # Should include only current child in all_inputs
        all_inputs = switch.all_inputs
        assert len(all_inputs) == 1
        assert switch.current_child in all_inputs

    def test_initialization_with_partial_modes(self):
        """Test ModeSwitch initialization with only some mode nodes"""
        rave_node = Mock(spec=BaseInterpretationNode)
        blackout_node = Mock(spec=BaseInterpretationNode)
        gentle_node = Mock(spec=BaseInterpretationNode)
        chill_node = Mock(spec=BaseInterpretationNode)

        switch = ModeSwitch(
            rave=rave_node, blackout=blackout_node, gentle=gentle_node, chill=chill_node
        )

        # Should have all provided mode nodes
        assert switch.mode_nodes[Mode.rave] == rave_node
        assert switch.mode_nodes[Mode.blackout] == blackout_node
        assert switch.mode_nodes[Mode.gentle] == gentle_node
        assert switch.mode_nodes[Mode.chill] == chill_node

        # Should include only current child in all_inputs
        all_inputs = switch.all_inputs
        assert len(all_inputs) == 1
        assert switch.current_child in all_inputs

    def test_initialization_with_kwargs(self):
        """Test ModeSwitch initialization using kwargs for mode names"""
        rave_node = Mock(spec=BaseInterpretationNode)
        blackout_node = Mock(spec=BaseInterpretationNode)
        gentle_node = Mock(spec=BaseInterpretationNode)
        chill_node = Mock(spec=BaseInterpretationNode)

        switch = ModeSwitch(
            rave=rave_node, blackout=blackout_node, gentle=gentle_node, chill=chill_node
        )

        assert switch.mode_nodes[Mode.rave] == rave_node
        assert switch.mode_nodes[Mode.blackout] == blackout_node
        assert switch.mode_nodes[Mode.gentle] == gentle_node
        assert switch.mode_nodes[Mode.chill] == chill_node

    def test_initialization_empty_raises_error(self):
        """Test that initialization with no nodes raises an error"""
        with pytest.raises(TypeError, match="missing.*required.*arguments"):
            ModeSwitch()

    def test_initialization_invalid_mode_raises_error(self):
        """Test that initialization with invalid mode name raises an error"""
        rave_node = Mock(spec=BaseInterpretationNode)

        with pytest.raises(TypeError, match="unexpected keyword argument"):
            ModeSwitch(rave=rave_node, invalid_mode=Mock())

    def test_enter_exit_lifecycle(self):
        """Test enter/exit lifecycle management"""
        rave_node = Mock(spec=BaseInterpretationNode)
        blackout_node = Mock(spec=BaseInterpretationNode)
        gentle_node = Mock(spec=BaseInterpretationNode)
        chill_node = Mock(spec=BaseInterpretationNode)
        switch = ModeSwitch(
            rave=rave_node, blackout=blackout_node, gentle=gentle_node, chill=chill_node
        )
        context = Mock(spec=mgl.Context)

        # Test enter - should only call enter_recursive on current_child
        switch.enter(context)
        switch.current_child.enter_recursive.assert_called_once_with(context)
        assert switch._context == context

        # Test exit - should only call exit_recursive on current_child
        switch.exit()
        switch.current_child.exit_recursive.assert_called_once()
        assert switch._context is None

    def test_generate_switches_to_available_mode(self):
        """Test that generate switches to the correct mode when available"""
        rave_node = Mock(spec=BaseInterpretationNode)
        blackout_node = Mock(spec=BaseInterpretationNode)
        gentle_node = Mock(spec=BaseInterpretationNode)
        chill_node = Mock(spec=BaseInterpretationNode)
        switch = ModeSwitch(
            rave=rave_node, blackout=blackout_node, gentle=gentle_node, chill=chill_node
        )

        # Test with rave mode - should use rave node
        rave_vibe = Vibe(Mode.rave)
        switch.generate(rave_vibe)
        assert switch.current_child == rave_node
        switch.current_child.generate_recursive.assert_called_once_with(rave_vibe)

        # Reset and test with blackout mode - should switch to blackout node
        switch.current_child.generate_recursive.reset_mock()
        blackout_vibe = Vibe(Mode.blackout)
        switch.generate(blackout_vibe)
        assert switch.current_child == blackout_node
        switch.current_child.generate_recursive.assert_called_once_with(blackout_vibe)

    def test_generate_keeps_current_when_mode_unavailable(self):
        """Test that generate keeps current child when switching to same mode"""
        rave_node = Mock(spec=BaseInterpretationNode)
        blackout_node = Mock(spec=BaseInterpretationNode)
        gentle_node = Mock(spec=BaseInterpretationNode)
        chill_node = Mock(spec=BaseInterpretationNode)
        switch = ModeSwitch(
            rave=rave_node, blackout=blackout_node, gentle=gentle_node, chill=chill_node
        )

        # Start with rave mode
        rave_vibe = Vibe(Mode.rave)
        switch.generate(rave_vibe)
        assert switch.current_child == rave_node

        # Switch to same mode again - should keep current child
        rave_vibe2 = Vibe(Mode.rave)
        switch.generate(rave_vibe2)
        assert switch.current_child == rave_node  # Should remain rave

    def test_render_current_child(self):
        """Test render uses current_child"""
        rave_node = Mock(spec=BaseInterpretationNode)
        blackout_node = Mock(spec=BaseInterpretationNode)
        gentle_node = Mock(spec=BaseInterpretationNode)
        chill_node = Mock(spec=BaseInterpretationNode)
        switch = ModeSwitch(
            rave=rave_node, blackout=blackout_node, gentle=gentle_node, chill=chill_node
        )

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
        chill_node = Mock(spec=BaseInterpretationNode)
        switch = ModeSwitch(
            rave=rave_node, blackout=blackout_node, gentle=gentle_node, chill=chill_node
        )

        # Mock objects
        frame = Mock(spec=Frame)
        scheme = Mock(spec=ColorScheme)
        context = Mock(spec=mgl.Context)

        mock_rave_framebuffer = Mock(spec=mgl.Framebuffer)
        mock_blackout_framebuffer = Mock(spec=mgl.Framebuffer)
        mock_gentle_framebuffer = Mock(spec=mgl.Framebuffer)
        mock_chill_framebuffer = Mock(spec=mgl.Framebuffer)

        rave_node.render = Mock(return_value=mock_rave_framebuffer)
        blackout_node.render = Mock(return_value=mock_blackout_framebuffer)
        gentle_node.render = Mock(return_value=mock_gentle_framebuffer)
        chill_node.render = Mock(return_value=mock_chill_framebuffer)

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

        # Switch to chill mode
        switch.generate(Vibe(Mode.chill))
        assert switch.current_child == chill_node
        result = switch.render(frame, scheme, context)
        assert result == mock_chill_framebuffer

    def test_enter_exit_on_switch(self):
        """Test that enter/exit is called when switching children"""
        rave_node = Mock(spec=BaseInterpretationNode)
        blackout_node = Mock(spec=BaseInterpretationNode)
        gentle_node = Mock(spec=BaseInterpretationNode)
        chill_node = Mock(spec=BaseInterpretationNode)
        switch = ModeSwitch(
            rave=rave_node, blackout=blackout_node, gentle=gentle_node, chill=chill_node
        )
        context = Mock(spec=mgl.Context)

        # Enter the switch (should enter current child)
        switch.enter(context)
        switch.current_child.enter_recursive.assert_called_once_with(context)

        # Determine which node was the initial current_child
        initial_child = switch.current_child

        # Pick a different mode to switch to
        if initial_child == rave_node:
            other_child = blackout_node
            other_mode = Mode.blackout
            initial_mode = Mode.rave
        elif initial_child == blackout_node:
            other_child = gentle_node
            other_mode = Mode.gentle
            initial_mode = Mode.blackout
        elif initial_child == gentle_node:
            other_child = chill_node
            other_mode = Mode.chill
            initial_mode = Mode.gentle
        else:  # initial_child == chill_node
            other_child = rave_node
            other_mode = Mode.rave
            initial_mode = Mode.chill

        initial_child.enter_recursive.reset_mock()

        # Switch to the other mode (should exit current child and enter other child)
        switch.generate(Vibe(other_mode))
        initial_child.exit_recursive.assert_called_once()
        other_child.enter_recursive.assert_called_once_with(context)

        # Reset mocks
        initial_child.exit_recursive.reset_mock()
        other_child.enter_recursive.reset_mock()

        # Switch back (should exit other child and enter initial child)
        switch.generate(Vibe(initial_mode))
        other_child.exit_recursive.assert_called_once()
        initial_child.enter_recursive.assert_called_once_with(context)

    def test_mode_switching_preserves_state(self):
        """Test that mode switching preserves the current state correctly"""
        rave_node = Mock(spec=BaseInterpretationNode)
        blackout_node = Mock(spec=BaseInterpretationNode)
        gentle_node = Mock(spec=BaseInterpretationNode)
        chill_node = Mock(spec=BaseInterpretationNode)
        switch = ModeSwitch(
            rave=rave_node, blackout=blackout_node, gentle=gentle_node, chill=chill_node
        )
        context = Mock(spec=mgl.Context)

        # Enter the switch
        switch.enter(context)
        initial_child = switch.current_child
        initial_child.enter_recursive.assert_called_once_with(context)
        initial_child.enter_recursive.reset_mock()

        # Switch to same mode - should not trigger enter/exit
        if initial_child == rave_node:
            switch.generate(Vibe(Mode.rave))
        elif initial_child == blackout_node:
            switch.generate(Vibe(Mode.blackout))
        elif initial_child == gentle_node:
            switch.generate(Vibe(Mode.gentle))
        else:  # chill_node
            switch.generate(Vibe(Mode.chill))

        initial_child.exit_recursive.assert_not_called()
        initial_child.enter_recursive.assert_not_called()
        assert switch.current_child == initial_child


if __name__ == "__main__":
    pytest.main([__file__])
