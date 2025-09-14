#!/usr/bin/env python3

import moderngl as mgl
from beartype import beartype

from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.director.frame import Frame
from parrot.director.color_scheme import ColorScheme


@beartype
class Black(BaseInterpretationNode[mgl.Context, None, mgl.Framebuffer]):
    """
    A simple black background node.
    """

    def __init__(self):
        super().__init__([])
        self.framebuffer = None

    def enter(self, context: mgl.Context):
        """Initialize black background resources"""
        # Create a black texture and framebuffer
        texture = context.texture((1920, 1080), 3)
        texture.write(b"\x00" * (1920 * 1080 * 3))  # Black pixels
        self.framebuffer = context.framebuffer(color_attachments=[texture])

    def exit(self):
        """Clean up resources"""
        if self.framebuffer:
            self.framebuffer.release()
            self.framebuffer = None

    def generate(self, vibe: Vibe):
        """Nothing to generate for black background"""
        pass

    def render(
        self, frame: Frame, scheme: ColorScheme, context: mgl.Context
    ) -> mgl.Framebuffer:
        """Render black background"""
        # Resources should already be allocated in enter()
        return self.framebuffer
