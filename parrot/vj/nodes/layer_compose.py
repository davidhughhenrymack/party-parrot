#!/usr/bin/env python3

import numpy as np
import moderngl as mgl
from typing import List
from beartype import beartype

from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.director.frame import Frame
from parrot.director.color_scheme import ColorScheme


@beartype
class LayerCompose(BaseInterpretationNode[mgl.Context, None, mgl.Framebuffer]):
    """
    A composition node that layers multiple effects and video sources.
    Composites layers using their alpha channels for proper blending.
    """

    def __init__(self, *layers: BaseInterpretationNode):
        # Pass layers as children to super - this handles enter/exit/generate recursively
        super().__init__(list(layers))
        self.layers = list(layers)
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

    def _setup_gl_resources(
        self, context: mgl.Context, width: int = 1920, height: int = 1080
    ):
        """Setup OpenGL resources for layer compositing"""
        if not self.texture:
            self.texture = context.texture(
                (width, height), 4
            )  # RGBA texture for alpha blending
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

            # Fragment shader for alpha blending
            fragment_shader = """
            #version 330 core
            in vec2 uv;
            out vec4 color;
            uniform sampler2D base_texture;
            uniform sampler2D overlay_texture;
            uniform float overlay_alpha;
            
            void main() {
                vec4 base = texture(base_texture, uv);
                vec4 overlay = texture(overlay_texture, uv);
                
                // Alpha blending: result = overlay * overlay.a + base * (1 - overlay.a)
                float alpha = overlay.a * overlay_alpha;
                color = vec4(
                    overlay.rgb * alpha + base.rgb * (1.0 - alpha),
                    max(base.a, alpha)
                );
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
        Render all layers and composite them using alpha blending.
        Layers are composited from bottom to top (first layer is background).
        """
        if not self.layers:
            # Return empty black framebuffer
            self.framebuffer.use()
            context.clear(0.0, 0.0, 0.0, 1.0)
            return self.framebuffer

        # Render first layer as base
        base_framebuffer = self.layers[0].render(frame, scheme, context)

        if len(self.layers) == 1:
            # Only one layer, return it directly
            return base_framebuffer

        # Start with the base layer
        current_result = base_framebuffer

        # Composite each additional layer on top
        for i in range(1, len(self.layers)):
            overlay_framebuffer = self.layers[i].render(frame, scheme, context)

            if overlay_framebuffer is None:
                continue

            # Create a temporary framebuffer for the composite result
            temp_texture = context.texture((1920, 1080), 4)
            temp_framebuffer = context.framebuffer(color_attachments=[temp_texture])

            # Composite overlay onto current result
            temp_framebuffer.use()
            context.clear(0.0, 0.0, 0.0, 0.0)

            # Enable blending
            context.enable(mgl.BLEND)
            context.blend_func = mgl.SRC_ALPHA, mgl.ONE_MINUS_SRC_ALPHA

            # Bind textures
            if current_result and current_result.color_attachments:
                current_result.color_attachments[0].use(0)
            if overlay_framebuffer.color_attachments:
                overlay_framebuffer.color_attachments[0].use(1)

            # Set uniforms and render
            self.shader_program["base_texture"] = 0
            self.shader_program["overlay_texture"] = 1
            self.shader_program["overlay_alpha"] = 1.0

            self.quad_vao.render(mgl.TRIANGLE_STRIP)

            context.disable(mgl.BLEND)

            # Update current result
            current_result = temp_framebuffer

        return current_result
