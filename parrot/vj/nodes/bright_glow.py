#!/usr/bin/env python3

import numpy as np
import moderngl as mgl
from typing import Optional
from beartype import beartype

from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.graph.BaseInterpretationNode import format_node_status
from parrot.director.frame import Frame
from parrot.director.color_scheme import ColorScheme
from parrot.vj.nodes.canvas_effect_base import PostProcessEffectBase


@beartype
class BrightGlow(PostProcessEffectBase):
    """
    A bright glow effect that extracts bright pixels and blends them back as a blur.
    Creates a luminous glow around bright areas, perfect for CRT screen effects.

    Process:
    1. Extract pixels above brightness threshold (75%+)
    2. Blur the extracted bright areas
    3. Blend the blur back at low opacity (10%) for subtle glow
    """

    def __init__(
        self,
        input_node: BaseInterpretationNode,
        brightness_threshold: float = 0.75,
        blur_radius: int = 8,
        glow_intensity: float = 0.1,
    ):
        """
        Args:
            input_node: The node that provides the video input
            brightness_threshold: Minimum brightness to extract (0.0-1.0)
            blur_radius: Number of blur passes for the glow
            glow_intensity: Opacity of the glow blend (0.0-1.0)
        """
        super().__init__(input_node)
        self.brightness_threshold = brightness_threshold
        self.blur_radius = blur_radius
        self.glow_intensity = glow_intensity

        # Intermediate framebuffers for multi-pass rendering
        self.threshold_fbo = None
        self.blur_h_fbo = None
        self.blur_v_fbo = None

        # Shader programs and VAOs
        self.threshold_program = None
        self.threshold_vao = None
        self.blur_program = None
        self.blur_vao = None
        self.compose_program = None
        self.compose_vao = None

    def generate(self, vibe: Vibe):
        """Configure glow parameters based on the vibe"""
        # Keep parameters stable for consistent CRT effect
        pass

    def print_self(self) -> str:
        """Return class name with current parameters"""
        return format_node_status(
            self.__class__.__name__,
            emoji="✨",
            threshold=self.brightness_threshold,
            intensity=self.glow_intensity,
        )

    def enter(self, context):
        """Initialize OpenGL resources"""
        super().enter(context)

        # Framebuffers will be created dynamically based on input size
        # Store current size to detect when resize is needed
        self._current_width = 0
        self._current_height = 0

        # Create a fullscreen quad VBO with position + texcoord
        vertices = np.array(
            [
                # Position      # TexCoord
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
        quad_vbo = context.buffer(vertices.tobytes())

        # Create threshold extraction shader
        self.threshold_program = context.program(
            vertex_shader=self._get_vertex_shader(),
            fragment_shader=self._get_threshold_shader(),
        )

        # Create VAO for threshold program
        self.threshold_vao = context.vertex_array(
            self.threshold_program,
            [(quad_vbo, "2f 2f", "in_position", "in_texcoord")],
        )

        # Create blur shader
        self.blur_program = context.program(
            vertex_shader=self._get_vertex_shader(),
            fragment_shader=self._get_blur_shader(),
        )

        # Create VAO for blur program
        self.blur_vao = context.vertex_array(
            self.blur_program,
            [(quad_vbo, "2f 2f", "in_position", "in_texcoord")],
        )

        # Create composition shader
        self.compose_program = context.program(
            vertex_shader=self._get_vertex_shader(),
            fragment_shader=self._get_compose_shader(),
        )

        # Create VAO for compose program
        self.compose_vao = context.vertex_array(
            self.compose_program,
            [(quad_vbo, "2f 2f", "in_position", "in_texcoord")],
        )

    def _get_threshold_shader(self) -> str:
        """Shader that extracts bright pixels above threshold"""
        return """
        #version 330 core
        in vec2 uv;
        out vec3 color;
        uniform sampler2D input_texture;
        uniform float brightness_threshold;
        
        void main() {
            vec3 input_color = texture(input_texture, uv).rgb;
            
            // Calculate perceived brightness (luminance)
            float brightness = dot(input_color, vec3(0.299, 0.587, 0.114));
            
            // Extract only pixels above threshold
            if (brightness >= brightness_threshold) {
                color = input_color;
            } else {
                color = vec3(0.0);
            }
        }
        """

    def _get_blur_shader(self) -> str:
        """Gaussian blur shader (separable, single direction)"""
        return """
        #version 330 core
        in vec2 uv;
        out vec3 color;
        uniform sampler2D input_texture;
        uniform vec2 blur_direction;
        
        void main() {
            vec2 tex_offset = 1.0 / textureSize(input_texture, 0);
            vec3 result = vec3(0.0);
            
            // 9-tap Gaussian blur
            float weights[5] = float[](0.227027, 0.1945946, 0.1216216, 0.054054, 0.016216);
            
            result += texture(input_texture, uv).rgb * weights[0];
            
            for(int i = 1; i < 5; i++) {
                vec2 offset = blur_direction * tex_offset * float(i);
                result += texture(input_texture, uv + offset).rgb * weights[i];
                result += texture(input_texture, uv - offset).rgb * weights[i];
            }
            
            color = result;
        }
        """

    def _get_compose_shader(self) -> str:
        """Shader that blends original with glow"""
        return """
        #version 330 core
        in vec2 uv;
        out vec3 color;
        uniform sampler2D original_texture;
        uniform sampler2D glow_texture;
        uniform float glow_intensity;
        
        void main() {
            vec3 original = texture(original_texture, uv).rgb;
            vec3 glow = texture(glow_texture, uv).rgb;
            
            // Additive blend with glow intensity
            color = original + glow * glow_intensity;
        }
        """

    def _ensure_framebuffer_size(self, context, width: int, height: int):
        """Ensure framebuffers match the input size, recreate if needed"""
        if self._current_width == width and self._current_height == height:
            return  # Already the right size

        # Release old framebuffers if they exist
        if self.threshold_fbo:
            self.threshold_fbo.release()
        if self.blur_h_fbo:
            self.blur_h_fbo.release()
        if self.blur_v_fbo:
            self.blur_v_fbo.release()

        # Create new framebuffers with correct size
        self.threshold_fbo = context.framebuffer(
            color_attachments=[context.texture((width, height), 3, dtype="f4")]
        )

        self.blur_h_fbo = context.framebuffer(
            color_attachments=[context.texture((width, height), 3, dtype="f4")]
        )

        self.blur_v_fbo = context.framebuffer(
            color_attachments=[context.texture((width, height), 3, dtype="f4")]
        )

        self._current_width = width
        self._current_height = height

    def _render_with_program(
        self, vao, program, input_texture, output_fbo, uniforms: dict = None
    ):
        """Helper to render with a shader program"""
        output_fbo.use()
        output_fbo.clear(0.0, 0.0, 0.0)

        input_texture.use(0)
        program["input_texture"] = 0

        if uniforms:
            for name, value in uniforms.items():
                program[name] = value

        # Render the quad using the provided VAO
        vao.render(mgl.TRIANGLE_STRIP)

    def _get_fragment_shader(self) -> str:
        """Required by PostProcessEffectBase but not used (we have custom rendering)"""
        return """
        #version 330 core
        in vec2 uv;
        out vec3 color;
        uniform sampler2D input_texture;
        void main() {
            color = texture(input_texture, uv).rgb;
        }
        """

    def _set_effect_uniforms(self, frame: Frame, scheme: ColorScheme):
        """This method is called by PostProcessEffectBase but we handle rendering differently"""
        pass

    def render(
        self, frame: Frame, scheme: ColorScheme, context
    ) -> "Optional[mgl.Framebuffer]":
        """Multi-pass rendering: threshold -> blur -> compose"""
        # Get input from child node
        input_fb = self.input_node.render(frame, scheme, context)
        if input_fb is None:
            return None

        # Ensure all framebuffers match the input size
        input_width = input_fb.width
        input_height = input_fb.height
        self._ensure_framebuffer_size(context, input_width, input_height)

        # Pass 1: Extract bright pixels above threshold
        self._render_with_program(
            self.threshold_vao,
            self.threshold_program,
            input_fb.color_attachments[0],
            self.threshold_fbo,
            {"brightness_threshold": self.brightness_threshold},
        )

        # Pass 2: Horizontal blur
        self._render_with_program(
            self.blur_vao,
            self.blur_program,
            self.threshold_fbo.color_attachments[0],
            self.blur_h_fbo,
            {"blur_direction": (1.0, 0.0)},
        )

        # Pass 3: Vertical blur (applied multiple times for stronger blur)
        current_input = self.blur_h_fbo.color_attachments[0]
        for i in range(self.blur_radius):
            output_fbo = self.blur_v_fbo if i % 2 == 0 else self.blur_h_fbo
            self._render_with_program(
                self.blur_vao,
                self.blur_program,
                current_input,
                output_fbo,
                {"blur_direction": (0.0, 1.0)},
            )
            current_input = output_fbo.color_attachments[0]

        # Pass 4: Compose original with blurred glow
        # Ensure output framebuffer matches input size
        if (
            not self.framebuffer
            or self.framebuffer.width != input_width
            or self.framebuffer.height != input_height
        ):
            if self.framebuffer:
                self.framebuffer.release()
            self.framebuffer = context.framebuffer(
                color_attachments=[context.texture((input_width, input_height), 3)]
            )

        self.framebuffer.use()
        self.framebuffer.clear(0.0, 0.0, 0.0)

        input_fb.color_attachments[0].use(0)
        current_input.use(1)

        self.compose_program["original_texture"] = 0
        self.compose_program["glow_texture"] = 1
        self.compose_program["glow_intensity"] = self.glow_intensity

        self.compose_vao.render(mgl.TRIANGLE_STRIP)

        return self.framebuffer

    def exit(self):
        """Release OpenGL resources"""
        if self.threshold_fbo:
            self.threshold_fbo.release()
        if self.blur_h_fbo:
            self.blur_h_fbo.release()
        if self.blur_v_fbo:
            self.blur_v_fbo.release()
        if self.threshold_vao:
            self.threshold_vao.release()
        if self.threshold_program:
            self.threshold_program.release()
        if self.blur_vao:
            self.blur_vao.release()
        if self.blur_program:
            self.blur_program.release()
        if self.compose_vao:
            self.compose_vao.release()
        if self.compose_program:
            self.compose_program.release()

        super().exit()
