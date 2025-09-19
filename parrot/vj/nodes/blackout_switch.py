#!/usr/bin/env python3

import moderngl as mgl
from typing import Optional
from beartype import beartype

from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.director.frame import Frame
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode
from parrot.vj.nodes.black import Black


@beartype
class BlackoutSwitch(BaseInterpretationNode[mgl.Context, None, mgl.Framebuffer]):
    """
    A node that switches between its child and a black node based on the mode.
    The current_child is set during generate() and render() simply renders the current child.
    Enter/exit lifecycle is called on each switch.
    """

    def __init__(
        self, child: BaseInterpretationNode[mgl.Context, None, mgl.Framebuffer]
    ):
        super().__init__([child])
        self.child = child
        self.black_node = Black()
        self.current_child = child  # Start with the main child
        self._context: Optional[mgl.Context] = None

    @property
    def all_inputs(self):
        """Include both child and black node as inputs"""
        return [self.child, self.black_node]

    def enter(self, context: mgl.Context):
        """Initialize the current child only"""
        self._context = context
        self.current_child.enter(context)

    def exit(self):
        """Clean up the current child only"""
        self.current_child.exit()
        self._context = None

    def generate(self, vibe: Vibe):
        """Switch current child based on mode and handle enter/exit lifecycle"""
        # Determine which child should be active
        new_child = self.black_node if vibe.mode == Mode.blackout else self.child

        # If switching children, handle enter/exit lifecycle
        if new_child != self.current_child and self._context is not None:
            # Exit the old child
            self.current_child.exit()
            # Switch to new child
            self.current_child = new_child
            # Enter the new child
            self.current_child.enter(self._context)
        else:
            # Just update current_child (for initial case or when context not set)
            self.current_child = new_child

        # Generate for the current child
        self.current_child.generate(vibe)

    def render(
        self, frame: Frame, scheme: ColorScheme, context: mgl.Context
    ) -> Optional[mgl.Framebuffer]:
        """Render the current child"""
        return self.current_child.render(frame, scheme, context)
