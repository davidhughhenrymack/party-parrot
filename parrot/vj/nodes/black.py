#!/usr/bin/env python3

import moderngl as mgl
from typing import Optional
from beartype import beartype

from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.director.frame import Frame
from parrot.director.color_scheme import ColorScheme
from parrot.vj.constants import DEFAULT_WIDTH, DEFAULT_HEIGHT


@beartype
class Black(BaseInterpretationNode[mgl.Context, None, mgl.Framebuffer]):
    """
    A simple black background node that renders solid black.
    Useful as a base layer for composition.
    """

    def __init__(self, width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT):
        super().__init__([])  # No children
        self.width = width
        self.height = height
        self.framebuffer: Optional[mgl.Framebuffer] = None
        self.texture: Optional[mgl.Texture] = None
        self._context: Optional[mgl.Context] = None

    def enter(self, context: mgl.Context):
        """Initialize black framebuffer"""
        self._context = context

        # Create black texture and framebuffer
        self.texture = context.texture((self.width, self.height), 4)  # RGBA
        self.framebuffer = context.framebuffer(color_attachments=[self.texture])

    def exit(self):
        """Clean up resources"""
        if self.framebuffer:
            self.framebuffer.release()
            self.framebuffer = None
        if self.texture:
            self.texture.release()
            self.texture = None
        self._context = None

    def generate(self, vibe: Vibe):
        """Nothing to generate for black background"""
        pass

    def render(
        self, frame: Frame, scheme: ColorScheme, context: mgl.Context
    ) -> Optional[mgl.Framebuffer]:
        """Render solid black"""
        if not self.framebuffer:
            return None

        # Clear to solid black
        self.framebuffer.use()
        context.clear(0.0, 0.0, 0.0, 1.0)  # Solid black with full alpha

        return self.framebuffer
