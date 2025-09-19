#!/usr/bin/env python3

import numpy as np
import moderngl as mgl
from abc import abstractmethod
from typing import Optional, Tuple
from beartype import beartype

from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.director.frame import Frame
from parrot.director.color_scheme import ColorScheme


@beartype
class CanvasEffectBase(
    BaseInterpretationNode[mgl.Context, mgl.Framebuffer, mgl.Framebuffer]
):
    """
    Base class for canvas effects that work with framebuffers.
    Provides common OpenGL resource management and shader utilities.
    """

    def __init__(self, input_node: Optional[BaseInterpretationNode] = None):
        """
        Args:
            input_node: Optional input node that provides a framebuffer
        """
        super().__init__([input_node] if input_node else [])
        self.input_node = input_node

        # Common OpenGL resources
        self.framebuffer: Optional[mgl.Framebuffer] = None
        self.texture: Optional[mgl.Texture] = None
        self.shader_program: Optional[mgl.Program] = None
        self.quad_vao: Optional[mgl.VertexArray] = None

    def enter(self, context: mgl.Context):
        """Initialize OpenGL resources"""
        self._setup_gl_resources(context)

    def exit(self):
        """Clean up OpenGL resources"""
        self._cleanup_gl_resources()

    def _cleanup_gl_resources(self):
        """Clean up all OpenGL resources"""
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

    def _setup_gl_resources(
        self, context: mgl.Context, width: int = 1920, height: int = 1080
    ):
        """Setup OpenGL resources for rendering"""
        if not self.texture:
            self.texture = context.texture((width, height), 3)  # RGB texture
            self.framebuffer = context.framebuffer(color_attachments=[self.texture])

        if not self.shader_program:
            vertex_shader = self._get_vertex_shader()
            fragment_shader = self._get_fragment_shader()
            self.shader_program = context.program(
                vertex_shader=vertex_shader, fragment_shader=fragment_shader
            )

        if not self.quad_vao:
            self.quad_vao = self._create_fullscreen_quad(context)

    def _get_vertex_shader(self) -> str:
        """Get the vertex shader source. Override for custom vertex shaders."""
        return """
        #version 330 core
        in vec2 in_position;
        in vec2 in_texcoord;
        out vec2 uv;
        
        void main() {
            gl_Position = vec4(in_position, 0.0, 1.0);
            uv = in_texcoord;
        }
        """

    @abstractmethod
    def _get_fragment_shader(self) -> str:
        """Get the fragment shader source. Must be implemented by subclasses."""
        pass

    def _create_fullscreen_quad(self, context: mgl.Context) -> mgl.VertexArray:
        """Create a fullscreen quad vertex array"""
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
        return context.vertex_array(
            self.shader_program, [(vbo, "2f 2f", "in_position", "in_texcoord")]
        )

    def _create_simple_quad(self, context: mgl.Context) -> mgl.VertexArray:
        """Create a simple quad without texture coordinates"""
        vertices = np.array(
            [
                -1.0,
                -1.0,  # Bottom-left
                1.0,
                -1.0,  # Bottom-right
                -1.0,
                1.0,  # Top-left
                1.0,
                1.0,  # Top-right
            ],
            dtype=np.float32,
        )

        vbo = context.buffer(vertices.tobytes())
        return context.vertex_array(self.shader_program, [(vbo, "2f", "in_position")])

    def _ensure_framebuffer_size(self, context: mgl.Context, width: int, height: int):
        """Ensure framebuffer matches the specified size, recreating if necessary"""
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
            self.framebuffer = None
            self.texture = None

            # Setup with new dimensions
            self._setup_gl_resources(context, width, height)

    def _get_input_framebuffer(
        self, frame: Frame, scheme: ColorScheme, context: mgl.Context
    ) -> Optional[mgl.Framebuffer]:
        """Get the input framebuffer from the input node, if any"""
        if self.input_node:
            return self.input_node.render(frame, scheme, context)
        return None

    def _render_black_framebuffer(self, context: mgl.Context) -> mgl.Framebuffer:
        """Render a black framebuffer as fallback"""
        if not self.framebuffer:
            self._setup_gl_resources(context)
        self.framebuffer.use()
        context.clear(0.0, 0.0, 0.0)
        return self.framebuffer

    def _safe_set_uniform(self, uniform_name: str, value):
        """
        Safely set a shader uniform, only if it exists in the compiled program.
        This prevents KeyError exceptions when uniforms are optimized away by the shader compiler.

        Args:
            uniform_name: Name of the uniform to set
            value: Value to set the uniform to

        Returns:
            bool: True if uniform was set, False if it doesn't exist
        """
        if not self.shader_program:
            return False

        try:
            # Check if uniform exists by trying to access it
            _ = self.shader_program[uniform_name]
            self.shader_program[uniform_name] = value
            return True
        except KeyError:
            # Uniform doesn't exist in compiled program (likely optimized away)
            return False


@beartype
class PostProcessEffectBase(CanvasEffectBase):
    """
    Base class for post-processing effects that take an input framebuffer and apply an effect.
    """

    def __init__(self, input_node: BaseInterpretationNode):
        """
        Args:
            input_node: The node that provides the input framebuffer
        """
        super().__init__(input_node)

    def render(
        self, frame: Frame, scheme: ColorScheme, context: mgl.Context
    ) -> mgl.Framebuffer:
        """
        Render the post-processing effect.
        Gets input from input_node, applies effect, returns result framebuffer.
        """
        # Get the input framebuffer
        input_framebuffer = self._get_input_framebuffer(frame, scheme, context)

        if not input_framebuffer or not input_framebuffer.color_attachments:
            return self._render_black_framebuffer(context)

        # Ensure our framebuffer matches input size
        input_width = input_framebuffer.width
        input_height = input_framebuffer.height
        self._ensure_framebuffer_size(context, input_width, input_height)

        # Render the effect
        self.framebuffer.use()
        context.clear(0.0, 0.0, 0.0)

        # Bind input texture
        input_framebuffer.color_attachments[0].use(0)
        self.shader_program["input_texture"] = 0

        # Set effect-specific uniforms
        self._set_effect_uniforms(frame, scheme)

        # Render
        self.quad_vao.render(mgl.TRIANGLE_STRIP)

        return self.framebuffer

    @abstractmethod
    def _set_effect_uniforms(self, frame: Frame, scheme: ColorScheme):
        """Set effect-specific uniforms. Must be implemented by subclasses."""
        pass


@beartype
class GenerativeEffectBase(CanvasEffectBase):
    """
    Base class for generative effects that create content without input.
    """

    def __init__(self, width: int = 1920, height: int = 1080):
        """
        Args:
            width: Width of the generated content
            height: Height of the generated content
        """
        super().__init__(None)
        self.width = width
        self.height = height

    def render(
        self, frame: Frame, scheme: ColorScheme, context: mgl.Context
    ) -> mgl.Framebuffer:
        """
        Render the generative effect.
        Creates content without input, returns result framebuffer.
        """
        if not self.framebuffer:
            self._setup_gl_resources(context, self.width, self.height)

        self.framebuffer.use()
        context.clear(0.0, 0.0, 0.0)

        # Set effect-specific uniforms
        self._set_effect_uniforms(frame, scheme)

        # Render
        self.quad_vao.render(mgl.TRIANGLE_STRIP)

        return self.framebuffer

    @abstractmethod
    def _set_effect_uniforms(self, frame: Frame, scheme: ColorScheme):
        """Set effect-specific uniforms. Must be implemented by subclasses."""
        pass
