"""512-channel DMX grid heatmap (32×16) for the desktop GL editor."""

from __future__ import annotations

import colorsys
import os
import struct

import moderngl as mgl
from beartype import beartype
from PIL import Image, ImageDraw, ImageFont

GRID_W = 32
GRID_H = 16

# Top band as a fraction of framebuffer height (title + subtitle).
HEADER_HEIGHT_FRAC = 0.11


def _channel_rgb(value: int) -> tuple[float, float, float]:
    x = max(0, min(255, int(value))) / 255.0
    r, g, b = colorsys.hsv_to_rgb((1.0 - x) * (220.0 / 360.0), 0.82, 0.15 + 0.85 * x)
    return (r, g, b)


def _pick_font(size: int) -> ImageFont.ImageFont:
    for path in (
        "/System/Library/Fonts/Supplemental/Arial Bold.ttf",
        "/System/Library/Fonts/Supplemental/Arial.ttf",
        "/Library/Fonts/Arial.ttf",
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ):
        if os.path.exists(path):
            return ImageFont.truetype(path, size)
    return ImageFont.load_default()


def _build_header_rgb_image(width: int, header_h: int) -> Image.Image:
    img = Image.new("RGB", (max(1, width), max(1, header_h)), (14, 14, 22))
    draw = ImageDraw.Draw(img)
    title_size = max(16, int(header_h * 0.30))
    sub_size = max(12, int(header_h * 0.20))
    font_title = _pick_font(title_size)
    font_sub = _pick_font(sub_size)
    title = "Party Parrot"
    subtitle = "DMX heatmap"
    bbox_t = draw.textbbox((0, 0), title, font=font_title)
    bbox_s = draw.textbbox((0, 0), subtitle, font=font_sub)
    h1 = bbox_t[3] - bbox_t[1]
    h2 = bbox_s[3] - bbox_s[1]
    gap = max(3, header_h // 18)
    total = h1 + gap + h2
    y0 = max(0, (header_h - total) // 2)
    cx = width // 2
    draw.text(
        (cx, y0 + h1 // 2),
        title,
        font=font_title,
        fill=(248, 248, 252),
        anchor="mm",
    )
    draw.text(
        (cx, y0 + h1 + gap + h2 // 2),
        subtitle,
        font=font_sub,
        fill=(168, 174, 198),
        anchor="mm",
    )
    # OpenGL expects first row = bottom of image for texture upload without flip in UV.
    return img.transpose(Image.FLIP_TOP_BOTTOM)


@beartype
class DmxHeatmapRenderer:
    """Renders a single-universe DMX snapshot to an offscreen RGB framebuffer."""

    def __init__(self) -> None:
        self._ctx: mgl.Context | None = None
        self._prog: mgl.Program | None = None
        self._header_prog: mgl.Program | None = None
        self._vao: mgl.VertexArray | None = None
        self._header_vao: mgl.VertexArray | None = None
        self._vbo: mgl.Buffer | None = None
        self._header_vbo: mgl.Buffer | None = None
        self._data_tex: mgl.Texture | None = None
        self._header_tex: mgl.Texture | None = None
        self._out_tex: mgl.Texture | None = None
        self._fbo: mgl.Framebuffer | None = None
        self._width = 0
        self._height = 0
        self._cached_header_key: tuple[int, int] | None = None

    def enter(self, context: mgl.Context) -> None:
        self._ctx = context
        vertex = """
        #version 330
        in vec2 in_pos;
        in vec2 in_uv;
        out vec2 v_uv;
        void main() {
            gl_Position = vec4(in_pos, 0.0, 1.0);
            v_uv = in_uv;
        }
        """
        fragment = """
        #version 330
        in vec2 v_uv;
        out vec3 out_color;
        uniform sampler2D data_tex;
        uniform vec2 grid_size;
        void main() {
            // Match PIL/header orientation: CPU row 0 is top of grid; GL v_uv.y=0 is bottom of quad.
            vec2 uv = vec2(v_uv.x, 1.0 - v_uv.y);
            vec2 cell = floor(uv * grid_size);
            vec2 center = (cell + 0.5) / grid_size;
            vec3 c = texture(data_tex, center).rgb;
            vec2 f = fract(uv * grid_size);
            float edge = max(step(0.88, f.x), step(0.88, f.y));
            c *= 1.0 - edge * 0.45;
            out_color = c;
        }
        """
        self._prog = context.program(vertex_shader=vertex, fragment_shader=fragment)
        header_fragment = """
        #version 330
        in vec2 v_uv;
        out vec3 out_color;
        uniform sampler2D header_tex;
        void main() {
            out_color = texture(header_tex, v_uv).rgb;
        }
        """
        self._header_prog = context.program(
            vertex_shader=vertex, fragment_shader=header_fragment
        )
        self._vbo = context.buffer(reserve=64)
        self._header_vbo = context.buffer(reserve=64)
        self._vao = context.vertex_array(
            self._prog, [(self._vbo, "2f 2f", "in_pos", "in_uv")]
        )
        self._header_vao = context.vertex_array(
            self._header_prog, [(self._header_vbo, "2f 2f", "in_pos", "in_uv")]
        )

    def resize(self, context: mgl.Context, width: int, height: int) -> None:
        if width <= 0 or height <= 0:
            return
        if self._width == width and self._height == height and self._out_tex is not None:
            return
        self._width = width
        self._height = height
        if self._out_tex is not None:
            self._out_tex.release()
        if self._fbo is not None:
            self._fbo.release()
        self._out_tex = context.texture((width, height), 3)
        self._fbo = context.framebuffer(color_attachments=[self._out_tex])
        self._cached_header_key = None

    def _ensure_header_texture(self, context: mgl.Context, width: int, height: int) -> None:
        header_h = max(1, int(round(height * HEADER_HEIGHT_FRAC)))
        key = (width, header_h)
        if self._header_tex is not None and self._cached_header_key == key:
            return
        if self._header_tex is not None:
            self._header_tex.release()
        img = _build_header_rgb_image(width, header_h)
        data = img.tobytes()
        self._header_tex = context.texture((width, header_h), 3, data=data)
        self._cached_header_key = key

    def _write_quad_vbo(
        self, vbo: mgl.Buffer, x0: float, y0: float, x1: float, y1: float
    ) -> None:
        """Full UV 0..1 over the quad (triangle strip: BL, BR, TL, TR)."""
        verts = (x0, y0, 0.0, 0.0, x1, y0, 1.0, 0.0, x0, y1, 0.0, 1.0, x1, y1, 1.0, 1.0)
        vbo.write(struct.pack("16f", *verts))

    def render(
        self, context: mgl.Context, snapshot_512: list[int], width: int, height: int
    ) -> mgl.Framebuffer | None:
        if self._prog is None or self._vao is None or self._header_prog is None:
            return None
        self.resize(context, width, height)
        if self._data_tex is None:
            self._data_tex = context.texture((GRID_W, GRID_H), 3, dtype="f4")
        data = bytearray(GRID_W * GRID_H * 3 * 4)
        for i in range(512):
            v = snapshot_512[i] if i < len(snapshot_512) else 0
            r, g, b = _channel_rgb(v)
            row = i // GRID_W
            col = i % GRID_W
            idx = (row * GRID_W + col) * 12
            packed = struct.pack("fff", r, g, b)
            data[idx : idx + 12] = packed
        self._data_tex.write(data)

        assert self._fbo is not None
        assert self._vbo is not None
        assert self._header_vbo is not None

        header_h = max(1, int(round(height * HEADER_HEIGHT_FRAC)))
        y_split = 1.0 - (2.0 * header_h / float(height))

        self._write_quad_vbo(self._vbo, -1.0, -1.0, 1.0, y_split)
        self._write_quad_vbo(self._header_vbo, -1.0, y_split, 1.0, 1.0)

        self._ensure_header_texture(context, width, height)
        assert self._header_tex is not None

        self._fbo.use()
        self._fbo.clear(0.02, 0.02, 0.06)

        self._data_tex.use(0)
        self._prog["data_tex"].value = 0
        self._prog["grid_size"].value = (float(GRID_W), float(GRID_H))
        self._vao.render(mgl.TRIANGLE_STRIP)

        self._header_tex.use(0)
        self._header_prog["header_tex"].value = 0
        self._header_vao.render(mgl.TRIANGLE_STRIP)
        return self._fbo
