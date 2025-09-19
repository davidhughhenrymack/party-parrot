#!/usr/bin/env python3

import os
import random
from typing import Optional, Union
import numpy as np
import moderngl as mgl
from PIL import Image, ImageDraw, ImageFont
from beartype import beartype

from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.director.frame import Frame
from parrot.director.color_scheme import ColorScheme
from parrot.vj.constants import DEFAULT_WIDTH, DEFAULT_HEIGHT


@beartype
class TextRenderer(BaseInterpretationNode[mgl.Context, None, mgl.Framebuffer]):
    """
    A text rendering node that renders text with configurable font, size, and colors.
    Text is centered both horizontally and vertically on the canvas.
    """

    def __init__(
        self,
        text: Union[str, list[str]] = "Hello World",
        font_name: str = "Arial",
        font_size: int = 48,
        width: int = DEFAULT_WIDTH,
        height: int = DEFAULT_HEIGHT,
        text_color: tuple[int, int, int] = (255, 255, 255),  # White text
        bg_color: tuple[int, int, int] = (0, 0, 0),  # Black background
    ):
        super().__init__([])
        # Handle both single text and list of texts
        if isinstance(text, str):
            self.text_options = [text]
        else:
            self.text_options = text
        self.current_text = self.text_options[0]  # Start with first option
        self.font_name = font_name
        self.font_size = font_size
        self.width = width
        self.height = height
        self.text_color = text_color
        self.bg_color = bg_color

        # OpenGL resources
        self.source_texture: Optional[mgl.Texture] = None  # Contains PIL image data
        self.target_texture: Optional[mgl.Texture] = (
            None  # Framebuffer color attachment
        )
        self.framebuffer: Optional[mgl.Framebuffer] = None
        self.quad_vao: Optional[mgl.VertexArray] = None
        self.shader_program: Optional[mgl.Program] = None
        self._context: Optional[mgl.Context] = None

        # Font and rendering
        self.font: Optional[ImageFont.ImageFont] = None
        self._text_image: Optional[Image.Image] = None
        self._needs_update = True

    def enter(self, context: mgl.Context):
        """Initialize text rendering resources"""
        self._context = context
        self._load_font()
        self._setup_gl_resources()
        self._render_text()

    def exit(self):
        """Clean up text rendering resources"""
        if self.source_texture:
            self.source_texture.release()
            self.source_texture = None
        if self.target_texture:
            self.target_texture.release()
            self.target_texture = None
        if self.framebuffer:
            self.framebuffer.release()
            self.framebuffer = None
        self._context = None

    def generate(self, vibe: Vibe):
        """Generate method - randomly select from available text options"""
        if len(self.text_options) > 1:
            new_text = random.choice(self.text_options)
            if new_text != self.current_text:
                self.current_text = new_text
                self._needs_update = True

    def _load_font(self):
        """Load the specified font"""
        try:
            # Try to load system font
            self.font = ImageFont.truetype(self.font_name, self.font_size)
        except (OSError, IOError):
            try:
                # Try common font paths on different systems
                font_paths = [
                    f"/System/Library/Fonts/{self.font_name}.ttf",  # macOS
                    f"/System/Library/Fonts/{self.font_name}.otf",  # macOS
                    f"/usr/share/fonts/truetype/dejavu/{self.font_name}.ttf",  # Linux
                    f"/Windows/Fonts/{self.font_name}.ttf",  # Windows
                    f"/Windows/Fonts/{self.font_name}.otf",  # Windows
                ]

                font_loaded = False
                for font_path in font_paths:
                    if os.path.exists(font_path):
                        self.font = ImageFont.truetype(font_path, self.font_size)
                        font_loaded = True
                        break

                if not font_loaded:
                    # Fallback to default font
                    print(
                        f"Warning: Could not load font '{self.font_name}', using default"
                    )
                    self.font = ImageFont.load_default()

            except Exception as e:
                print(f"Warning: Font loading failed: {e}, using default")
                self.font = ImageFont.load_default()

    def _setup_gl_resources(self):
        """Setup OpenGL resources for text rendering"""
        if not self._context:
            return

        # Create separate textures for source (PIL image) and target (framebuffer)
        if not self.source_texture:
            self.source_texture = self._context.texture(
                (self.width, self.height), 3
            )  # RGB
        if not self.target_texture:
            self.target_texture = self._context.texture(
                (self.width, self.height), 3
            )  # RGB
            self.framebuffer = self._context.framebuffer(
                color_attachments=[self.target_texture]
            )

        # Create shader program
        if not self.shader_program:
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

            fragment_shader = """
            #version 330 core
            in vec2 uv;
            out vec3 color;
            uniform sampler2D text_texture;
            
            void main() {
                color = texture(text_texture, uv).rgb;
            }
            """

            self.shader_program = self._context.program(
                vertex_shader=vertex_shader, fragment_shader=fragment_shader
            )

        # Create fullscreen quad
        if not self.quad_vao:
            vertices = np.array(
                [
                    # Position  # TexCoord
                    -1.0,
                    -1.0,
                    0.0,
                    0.0,  # Bottom-left -> (0,0) in texture
                    1.0,
                    -1.0,
                    1.0,
                    0.0,  # Bottom-right -> (1,0) in texture
                    -1.0,
                    1.0,
                    0.0,
                    1.0,  # Top-left -> (0,1) in texture
                    1.0,
                    1.0,
                    1.0,
                    1.0,  # Top-right -> (1,1) in texture
                ],
                dtype=np.float32,
            )

            vbo = self._context.buffer(vertices.tobytes())
            self.quad_vao = self._context.vertex_array(
                self.shader_program, [(vbo, "2f 2f", "in_position", "in_texcoord")]
            )

    def _render_text(self):
        """Render text to PIL image and upload to OpenGL texture"""
        if not self.font or not self.source_texture:
            return

        # Create PIL image with background color
        image = Image.new("RGB", (self.width, self.height), self.bg_color)
        draw = ImageDraw.Draw(image)

        # Draw text centered using anchor parameter
        # anchor='mm' means middle-middle (center both horizontally and vertically)
        center_x = self.width // 2
        center_y = self.height // 2
        draw.text(
            (center_x, center_y),
            self.current_text,
            fill=self.text_color,
            font=self.font,
            anchor="mm",
        )

        # Convert to numpy array and upload to texture
        # PIL uses RGB, OpenGL expects RGB - texture coordinates handle orientation
        image_array = np.array(image)

        self.source_texture.write(image_array.tobytes())
        self._needs_update = False

    def render(
        self, frame: Frame, scheme: ColorScheme, context: mgl.Context
    ) -> mgl.Framebuffer:
        """Render the text to framebuffer"""
        if not self.framebuffer or not self.quad_vao or not self.shader_program:
            raise RuntimeError(
                "TextRenderer not properly initialized. Call enter() first."
            )

        # Re-render text if needed
        if self._needs_update:
            self._render_text()

        # Render to framebuffer
        self.framebuffer.use()
        context.clear(0.0, 0.0, 0.0)

        self.source_texture.use(0)
        self.shader_program["text_texture"] = 0
        self.quad_vao.render(mgl.TRIANGLE_STRIP)

        return self.framebuffer

    def set_text(self, text: Union[str, list[str]]):
        """Update the text content - can be single text or list of texts"""
        if isinstance(text, str):
            new_options = [text]
        else:
            new_options = text

        if self.text_options != new_options:
            self.text_options = new_options
            self.current_text = self.text_options[0]
            self._needs_update = True

    def set_font_size(self, size: int):
        """Update the font size"""
        if self.font_size != size:
            self.font_size = size
            self._load_font()
            self._needs_update = True

    def set_colors(
        self, text_color: tuple[int, int, int], bg_color: tuple[int, int, int]
    ):
        """Update text and background colors"""
        if self.text_color != text_color or self.bg_color != bg_color:
            self.text_color = text_color
            self.bg_color = bg_color
            self._needs_update = True


# Convenience factory functions
def Text(
    text: Union[str, list[str]] = "Hello World",
    font_size: int = 48,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    **kwargs,
) -> TextRenderer:
    """Create a basic text renderer"""
    return TextRenderer(
        text=text, font_size=font_size, width=width, height=height, **kwargs
    )


def WhiteText(
    text: Union[str, list[str]] = "Hello World",
    font_size: int = 48,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    **kwargs,
) -> TextRenderer:
    """Create white text on black background"""
    return TextRenderer(
        text=text,
        font_size=font_size,
        width=width,
        height=height,
        text_color=(255, 255, 255),
        bg_color=(0, 0, 0),
        **kwargs,
    )


def BlackText(
    text: Union[str, list[str]] = "Hello World",
    font_size: int = 48,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    **kwargs,
) -> TextRenderer:
    """Create black text on white background"""
    return TextRenderer(
        text=text,
        font_size=font_size,
        width=width,
        height=height,
        text_color=(0, 0, 0),
        bg_color=(255, 255, 255),
        **kwargs,
    )


def ColorText(
    text: Union[str, list[str]] = "Hello World",
    text_color: tuple[int, int, int] = (255, 0, 0),  # Red
    bg_color: tuple[int, int, int] = (0, 0, 0),  # Black
    font_size: int = 48,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    **kwargs,
) -> TextRenderer:
    """Create colored text"""
    return TextRenderer(
        text=text,
        font_size=font_size,
        width=width,
        height=height,
        text_color=text_color,
        bg_color=bg_color,
        **kwargs,
    )


def ZombieText(
    font_size: int = 48,
    width: int = DEFAULT_WIDTH,
    height: int = DEFAULT_HEIGHT,
    **kwargs,
) -> TextRenderer:
    """Create zombie-themed text that shifts between different phrases"""
    zombie_texts = ["DEAD\nSEXY", "ZOMBIE\nYES", "BITE\nME"]
    return TextRenderer(
        text=zombie_texts,
        font_size=font_size,
        width=width,
        height=height,
        text_color=(255, 0, 0),  # Red text
        bg_color=(0, 0, 0),  # Black background
        **kwargs,
    )
