#!/usr/bin/env python3

import struct
import moderngl as mgl
from typing import List, Optional, Tuple
from enum import Enum
from beartype import beartype

from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.director.frame import Frame
from parrot.director.color_scheme import ColorScheme
from parrot.vj.constants import DEFAULT_WIDTH, DEFAULT_HEIGHT


class BlendMode(Enum):
    """Blend modes for layer composition"""

    NORMAL = "normal"  # Standard alpha blending
    ADDITIVE = "additive"  # Additive blending (for bright effects like lasers)
    MULTIPLY = "multiply"  # Multiplicative blending (for masks)
    SCREEN = "screen"  # Screen blending (for overlays)


@beartype
class LayerSpec:
    """Specification for a layer in the composition"""

    def __init__(
        self,
        node: BaseInterpretationNode,
        blend_mode: BlendMode = BlendMode.NORMAL,
        opacity: float = 1.0,
    ):
        self.node = node
        self.blend_mode = blend_mode
        self.opacity = opacity


@beartype
class LayerCompose(BaseInterpretationNode[mgl.Context, None, mgl.Framebuffer]):
    """
    A composition node that layers multiple effects and video sources with different blend modes.
    Supports alpha, additive, multiply, and screen blending modes.
    """

    def __init__(
        self,
        *layer_specs: LayerSpec,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT
    ):
        # Extract nodes for children management
        nodes = [spec.node for spec in layer_specs]
        super().__init__(nodes)

        self.layer_specs = list(layer_specs)
        self.width = width
        self.height = height

        # GL resources
        self.final_framebuffer: Optional[mgl.Framebuffer] = None
        self.final_texture: Optional[mgl.Texture] = None
        self.quad_program: Optional[mgl.Program] = None
        self.quad_vao: Optional[mgl.VertexArray] = None
        self._context: Optional[mgl.Context] = None

    def enter(self, context: mgl.Context):
        """Initialize compositing resources"""
        self._context = context
        self._create_fullscreen_quad(context)

        # Create final compositing framebuffer
        self.final_texture = context.texture((self.width, self.height), 4)  # RGBA
        self.final_framebuffer = context.framebuffer(
            color_attachments=[self.final_texture]
        )

    def exit(self):
        """Clean up compositing resources"""
        if self.final_framebuffer:
            self.final_framebuffer.release()
        if self.final_texture:
            self.final_texture.release()
        if self.quad_program:
            self.quad_program.release()
        if self.quad_vao:
            self.quad_vao.release()
        self._context = None

    def generate(self, vibe: Vibe):
        """Generate all layers - handled by base class recursive call"""
        pass

    def _create_fullscreen_quad(self, context: mgl.Context):
        """Create a fullscreen quad for texture compositing"""
        # Vertex shader for fullscreen quad
        vertex_shader = """
        #version 330 core
        in vec2 position;
        out vec2 uv;
        
        void main() {
            gl_Position = vec4(position, 0.0, 1.0);
            uv = position * 0.5 + 0.5;
        }
        """

        # Fragment shader for texture compositing with blend modes
        fragment_shader = """
        #version 330 core
        in vec2 uv;
        uniform sampler2D texture0;
        uniform float opacity;
        uniform int blend_mode;  // 0=normal, 1=additive, 2=multiply, 3=screen
        out vec4 color;
        
        void main() {
            vec4 tex_color = texture(texture0, uv);
            
            // Apply opacity
            tex_color.a *= opacity;
            
            // Set color based on blend mode (alpha handled by OpenGL blending)
            if (blend_mode == 2) {
                // Multiply: darken the image for masking
                color = vec4(tex_color.rgb, tex_color.a);
            } else {
                // Normal, additive, screen: use texture as-is
                color = tex_color;
            }
        }
        """

        # Create shader program
        self.quad_program = context.program(
            vertex_shader=vertex_shader, fragment_shader=fragment_shader
        )

        # Create fullscreen quad vertices
        quad_vertices = [
            -1.0,
            -1.0,  # Bottom-left
            1.0,
            -1.0,  # Bottom-right
            -1.0,
            1.0,  # Top-left
            1.0,
            1.0,  # Top-right
        ]

        # Create vertex buffer and vertex array
        quad_data = struct.pack("8f", *quad_vertices)
        quad_buffer = context.buffer(quad_data)
        self.quad_vao = context.vertex_array(
            self.quad_program, [(quad_buffer, "2f", "position")]
        )

    def _get_blend_func(self, blend_mode: BlendMode) -> Tuple[int, int]:
        """Get OpenGL blend function for blend mode"""
        if blend_mode == BlendMode.NORMAL:
            return mgl.SRC_ALPHA, mgl.ONE_MINUS_SRC_ALPHA
        elif blend_mode == BlendMode.ADDITIVE:
            return mgl.SRC_ALPHA, mgl.ONE
        elif blend_mode == BlendMode.MULTIPLY:
            return mgl.DST_COLOR, mgl.ZERO
        elif blend_mode == BlendMode.SCREEN:
            return mgl.ONE_MINUS_DST_COLOR, mgl.ONE
        else:
            return mgl.SRC_ALPHA, mgl.ONE_MINUS_SRC_ALPHA

    def _get_blend_mode_int(self, blend_mode: BlendMode) -> int:
        """Get integer value for blend mode uniform"""
        if blend_mode == BlendMode.NORMAL:
            return 0
        elif blend_mode == BlendMode.ADDITIVE:
            return 1
        elif blend_mode == BlendMode.MULTIPLY:
            return 2
        elif blend_mode == BlendMode.SCREEN:
            return 3
        else:
            return 0

    def _composite_layer(
        self,
        context: mgl.Context,
        texture: mgl.Texture,
        blend_mode: BlendMode,
        opacity: float,
    ):
        """Composite a layer texture onto the final framebuffer"""
        if not self.quad_program or not self.quad_vao:
            return

        # Get blend function
        blend_src, blend_dst = self._get_blend_func(blend_mode)

        # Set up blending
        context.enable(mgl.BLEND)
        context.blend_func = blend_src, blend_dst

        # Bind texture and set uniforms
        texture.use(location=0)
        self.quad_program["texture0"] = 0
        self.quad_program["opacity"] = opacity
        self.quad_program["blend_mode"] = self._get_blend_mode_int(blend_mode)

        # Render to final framebuffer
        self.final_framebuffer.use()
        self.quad_vao.render(mgl.TRIANGLE_STRIP)

        # Disable blending
        context.disable(mgl.BLEND)

    def render(
        self, frame: Frame, scheme: ColorScheme, context: mgl.Context
    ) -> Optional[mgl.Framebuffer]:
        """Render all layers and composite them with their specified blend modes"""
        if not self.final_framebuffer or not self.layer_specs:
            return None

        # Clear final framebuffer to transparent black
        self.final_framebuffer.use()
        context.clear(0.0, 0.0, 0.0, 0.0)

        # Render and composite each layer
        for i, layer_spec in enumerate(self.layer_specs):
            # Render the layer
            layer_result = layer_spec.node.render(frame, scheme, context)

            if not layer_result or not layer_result.color_attachments:
                continue

            if i == 0:
                # First layer: copy directly (base layer)
                context.copy_framebuffer(self.final_framebuffer, layer_result)
            else:
                # Subsequent layers: composite with blend mode
                self._composite_layer(
                    context,
                    layer_result.color_attachments[0],
                    layer_spec.blend_mode,
                    layer_spec.opacity,
                )

        return self.final_framebuffer
