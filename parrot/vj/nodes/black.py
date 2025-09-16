#!/usr/bin/env python3

import moderngl as mgl
from beartype import beartype

from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.director.frame import Frame
from parrot.director.color_scheme import ColorScheme


@beartype
class Black(BaseInterpretationNode[mgl.Context, None, mgl.Framebuffer]):
    """
    A simple black background node that adapts to requested size.
    """

    def __init__(self, width: int = 1920, height: int = 1080):
        super().__init__([])
        self.width = width
        self.height = height
        self.framebuffer = None
        self.texture = None

    def enter(self, context: mgl.Context):
        """Initialize black background resources"""
        self._setup_resources(context, self.width, self.height)

    def exit(self):
        """Clean up resources"""
        if self.framebuffer:
            self.framebuffer.release()
            self.framebuffer = None
        if self.texture:
            self.texture.release()
            self.texture = None

    def generate(self, vibe: Vibe):
        """Nothing to generate for black background"""
        pass

    def _setup_resources(self, context: mgl.Context, width: int, height: int):
        """Setup black framebuffer with specified dimensions"""
        if self.framebuffer:
            self.framebuffer.release()
        if self.texture:
            self.texture.release()

        # Create a black texture and framebuffer
        self.texture = context.texture((width, height), 3)
        self.texture.write(b"\x00" * (width * height * 3))  # Black pixels
        self.framebuffer = context.framebuffer(color_attachments=[self.texture])

    def render(
        self, frame: Frame, scheme: ColorScheme, context: mgl.Context
    ) -> mgl.Framebuffer:
        """Render black background"""
        # Ensure resources are allocated
        if not self.framebuffer:
            self._setup_resources(context, self.width, self.height)
        return self.framebuffer

    def render_with_size(
        self,
        frame: Frame,
        scheme: ColorScheme,
        context: mgl.Context,
        width: int,
        height: int,
    ) -> mgl.Framebuffer:
        """Render black background with specific size"""
        # Check if we need to recreate framebuffer for different size
        if (
            not self.framebuffer
            or self.framebuffer.width != width
            or self.framebuffer.height != height
        ):
            self._setup_resources(context, width, height)
        return self.framebuffer
