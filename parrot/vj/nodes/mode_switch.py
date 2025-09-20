#!/usr/bin/env python3

import logging
import moderngl as mgl
from typing import Optional, Dict
from beartype import beartype

from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.director.frame import Frame
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode

logger = logging.getLogger(__name__)


@beartype
class ModeSwitch(BaseInterpretationNode[mgl.Context, None, mgl.Framebuffer]):
    """
    A node that switches between different child nodes based on the current mode.
    Users provide a node for each mode as keyword arguments.
    The current_child is set during generate() and render() simply renders the current child.
    Enter/exit lifecycle is called on each switch.
    """

    def __init__(
        self,
        rave: BaseInterpretationNode[mgl.Context, None, mgl.Framebuffer],
        blackout: BaseInterpretationNode[mgl.Context, None, mgl.Framebuffer],
        gentle: BaseInterpretationNode[mgl.Context, None, mgl.Framebuffer],
    ):
        # Store mode nodes in a dictionary
        self.mode_nodes: Dict[
            Mode, BaseInterpretationNode[mgl.Context, None, mgl.Framebuffer]
        ] = {
            Mode.rave: rave,
            Mode.blackout: blackout,
            Mode.gentle: gentle,
        }

        super().__init__([])
        self.current_child = None
        self._context = None

    @property
    def all_inputs(self):
        """Return only the current child as input"""
        return [self.current_child] if self.current_child else []

    def enter(self, context: mgl.Context):
        """Initialize the current child only"""
        logger.debug("Entering ModeSwitch")
        self._context = context
        if self.current_child is not None:
            self.current_child.enter_recursive(context)

    def exit(self):
        """Clean up the current child only"""
        self._context = None
        if self.current_child is not None:
            self.current_child.exit_recursive()

    def generate(self, vibe: Vibe):
        """Switch current child based on mode and handle enter/exit lifecycle"""
        # Find the node for the current mode
        new_child = self.mode_nodes.get(vibe.mode)
        logger.debug(f"Generating ModeSwitch for mode: {vibe.mode}")
        logger.debug(f"Current child: {self.current_child}")
        logger.debug(f"New child: {new_child}")

        # If switching children, handle enter/exit lifecycle
        if new_child != self.current_child:
            # Exit the old child recursively
            if self.current_child is not None:
                self.current_child.exit_recursive()
            # Switch to new child
            self.current_child = new_child
            # Enter the new child recursively
            if self.current_child is not None and self._context is not None:
                self.current_child.enter_recursive(self._context)

        # Generate for the current child
        if self.current_child is not None:
            self.current_child.generate(vibe)

    def render(
        self, frame: Frame, scheme: ColorScheme, context: mgl.Context
    ) -> Optional[mgl.Framebuffer]:
        """Render the current child"""
        return self.current_child.render(frame, scheme, context)
