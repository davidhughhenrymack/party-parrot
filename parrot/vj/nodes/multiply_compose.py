#!/usr/bin/env python3

import numpy as np
import moderngl as mgl
from typing import List
from beartype import beartype

from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.director.frame import Frame
from parrot.director.color_scheme import ColorScheme
from parrot.vj.constants import DEFAULT_WIDTH, DEFAULT_HEIGHT


@beartype
class MultiplyCompose(BaseInterpretationNode[mgl.Context, None, mgl.Framebuffer]):
    """
    A composition node that multiplies two layers together.
    Perfect for applying text masks to video - white text shows video, black text hides it.

    The first layer is the base (typically video), the second is the mask (typically text).
    Result = base * mask (component-wise multiplication)
    """

    def __init__(
        self,
        base_layer: BaseInterpretationNode,
        mask_layer: BaseInterpretationNode,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
    ):
        # Pass layers as children to super - this handles enter/exit/generate recursively
        super().__init__([base_layer, mask_layer])
        self.base_layer = base_layer
        self.mask_layer = mask_layer
        self.width = width
        self.height = height
        self.framebuffer: mgl.Framebuffer = None
        self.texture: mgl.Texture = None
        self.shader_program: mgl.Program = None
        self.quad_vao: mgl.VertexArray = None

    def enter(self, context: mgl.Context):
        """Initialize compositing resources - children are handled by base class"""
        self._setup_gl_resources(context)

    def exit(self):
        """Clean up compositing resources - children are handled by base class"""
        if self.framebuffer:
            self.framebuffer.release()
            self.framebuffer = None
        if self.texture:
            self.texture.release()
            self.texture = None
        if self.shader_program:
            self.shader_program.release()
            self.shader_program = None
        if self.quad_vao:
            self.quad_vao.release()
            self.quad_vao = None

    def generate(self, vibe: Vibe):
        """Generate all layers - handled by base class recursive call"""
        pass

    def _setup_gl_resources(self, context: mgl.Context):
        """Setup OpenGL resources for multiplicative compositing"""
        if not self.texture:
            self.texture = context.texture((self.width, self.height), 3)  # RGB texture
            self.framebuffer = context.framebuffer(color_attachments=[self.texture])

        if not self.shader_program:
            # Vertex shader for fullscreen quad
            vertex_shader = """
            #version 330 core
            in vec2 in_position;
            in vec2 in_texcoord;
            out vec2 uv;
            
            void main() {
                gl_Position = vec4(in_position, 0.0, 1.0);
                uv = in_texcoord;
            }
            """

            # Fragment shader for multiplicative blending
            fragment_shader = """
            #version 330 core
            in vec2 uv;
            out vec3 color;
            uniform sampler2D base_texture;
            uniform sampler2D mask_texture;
            
            void main() {
                vec3 base = texture(base_texture, uv).rgb;
                vec3 mask = texture(mask_texture, uv).rgb;
                
                // Multiplicative blending: result = base * mask
                // White mask (1,1,1) shows full base, black mask (0,0,0) hides base
                color = base * mask;
            }
            """

            self.shader_program = context.program(
                vertex_shader=vertex_shader, fragment_shader=fragment_shader
            )

        if not self.quad_vao:
            # Create fullscreen quad
            vertices = np.array(
                [
                    # Position  # TexCoord
                    -1.0,
                    -1.0,
                    0.0,
                    0.0,  # Bottom-left
                    1.0,
                    -1.0,
                    1.0,
                    0.0,  # Bottom-right
                    -1.0,
                    1.0,
                    0.0,
                    1.0,  # Top-left
                    1.0,
                    1.0,
                    1.0,
                    1.0,  # Top-right
                ],
                dtype=np.float32,
            )

            vbo = context.buffer(vertices.tobytes())
            self.quad_vao = context.vertex_array(
                self.shader_program, [(vbo, "2f 2f", "in_position", "in_texcoord")]
            )

    def render(
        self, frame: Frame, scheme: ColorScheme, context: mgl.Context
    ) -> mgl.Framebuffer:
        """
        Render both layers and multiply them together.
        Base layer (typically video) is multiplied by mask layer (typically text).
        """
        # Render both layers
        base_framebuffer = self.base_layer.render(frame, scheme, context)
        mask_framebuffer = self.mask_layer.render(frame, scheme, context)

        if not base_framebuffer or not mask_framebuffer:
            # If either layer is missing, return black
            self.framebuffer.use()
            context.clear(0.0, 0.0, 0.0)
            return self.framebuffer

        # Ensure our framebuffer is set up
        if not self.framebuffer:
            self._setup_gl_resources(context)

        # Perform multiplicative composition
        self.framebuffer.use()
        context.clear(0.0, 0.0, 0.0)

        # Bind textures
        if base_framebuffer.color_attachments:
            base_framebuffer.color_attachments[0].use(0)
        if mask_framebuffer.color_attachments:
            mask_framebuffer.color_attachments[0].use(1)

        # Set uniforms and render
        self.shader_program["base_texture"] = 0
        self.shader_program["mask_texture"] = 1

        self.quad_vao.render(mgl.TRIANGLE_STRIP)

        return self.framebuffer
