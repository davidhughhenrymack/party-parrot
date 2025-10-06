#!/usr/bin/env python3

import logging
import moderngl as mgl
from typing import Optional, Dict, Any
from enum import Enum
from beartype import beartype
from colorama import Fore, Style

from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.graph.BaseInterpretationNode import format_node_status
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme

logger = logging.getLogger(__name__)


@beartype
class ModeSwitch(BaseInterpretationNode[mgl.Context, None, mgl.Framebuffer]):
    """
    A node that switches between different child nodes based on the current mode.
    Users provide a node for each mode as keyword arguments (matching enum value names).
    The current_child is set during generate() and render() simply renders the current child.
    Enter/exit lifecycle is called on each switch.

    Works with any Enum type (e.g., Mode, VJMode).
    """

    def __init__(
        self,
        **kwargs: BaseInterpretationNode[mgl.Context, None, mgl.Framebuffer],
    ):
        # Store mode nodes in a dictionary using keyword names
        # The enum values will be matched by name (e.g., 'rave', 'blackout', etc.)
        self.mode_nodes: Dict[
            str, BaseInterpretationNode[mgl.Context, None, mgl.Framebuffer]
        ] = kwargs

        super().__init__([])
        # Initialize with the first available mode node
        self.current_child = next(iter(self.mode_nodes.values()))
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
        # Find the node for the current mode by matching enum value name
        mode_name = vibe.mode.name if hasattr(vibe.mode, "name") else str(vibe.mode)
        new_child = self.mode_nodes.get(mode_name)
        logger.debug(f"Generating ModeSwitch for mode: {vibe.mode} (name: {mode_name})")
        logger.debug(f"Current child: {self.current_child}")
        logger.debug(f"New child: {new_child}")

        # If switching children, handle enter/exit lifecycle
        if new_child is not None and new_child != self.current_child:
            # Exit the old child recursively
            if self.current_child is not None:
                self.current_child.exit_recursive()
            # Switch to new child
            self.current_child = new_child
            # Enter the new child recursively
            if self.current_child is not None and self._context is not None:
                self.current_child.enter_recursive(self._context)

        # Generate for the current child recursively
        if self.current_child is not None:
            self.current_child.generate_recursive(vibe)

    def print_self(self) -> str:
        """Return class name with current mode"""
        mode_name = None
        if self.current_child is not None:
            for name, node in self.mode_nodes.items():
                if node == self.current_child:
                    mode_name = name
                    break
        mode_name = mode_name or "unknown"
        return format_node_status(
            self.__class__.__name__,
            emoji="🔀",
            signal=mode_name,
        )

    def render(
        self, frame: Frame, scheme: ColorScheme, context: mgl.Context
    ) -> Optional[mgl.Framebuffer]:
        """Render the current child"""
        return self.current_child.render(frame, scheme, context)
