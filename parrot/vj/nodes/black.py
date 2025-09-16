#!/usr/bin/env python3

import moderngl as mgl
from beartype import beartype

from parrot.vj.nodes.static_color import StaticColor
from parrot.director.frame import Frame
from parrot.director.color_scheme import ColorScheme
from parrot.vj.constants import DEFAULT_WIDTH, DEFAULT_HEIGHT


@beartype
class Black(StaticColor):
    """
    A simple black background node - subclass of StaticColor with black color.
    """

    def __init__(self, width: int = DEFAULT_WIDTH, height: int = DEFAULT_HEIGHT):
        # Initialize as StaticColor with black color (0.0, 0.0, 0.0)
        super().__init__(color=(0.0, 0.0, 0.0), width=width, height=height)

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
            # Clean up old resources
            if self.framebuffer:
                self.framebuffer.release()
            if self.texture:
                self.texture.release()

            # Create new resources with the requested size
            self.texture = context.texture((width, height), 3)
            self.framebuffer = context.framebuffer(color_attachments=[self.texture])

            # Update internal dimensions
            self.width = width
            self.height = height

            # Re-setup GL resources if needed
            if not self.shader_program or not self.quad_vao:
                self._setup_gl_resources(context)

        # Render using parent's render method
        return self.render(frame, scheme, context)
