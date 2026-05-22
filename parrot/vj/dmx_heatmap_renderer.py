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

# Grid quad in NDC: shrink and center below the header (1 = full width/height of grid band).
HEATMAP_NDC_SCALE = 0.68

# Per-cell: fraction of cell left as background gap on each side (square fill is centered).
CELL_GAP_FRAC = 0.09

# Fraction of the heatmap quad reserved on the left for row-start address labels
# (e.g. "1", "33", "65", …). The 32 data cells sit in the remaining width.
ROW_HEADER_WIDTH_FRAC = 0.07


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


def _build_overlay_rgba_image(
    overlay_w: int,
    overlay_h: int,
    row_header_w: int,
    snapshot_512: list[int],
) -> Image.Image:
    """RGBA overlay drawn over the heatmap quad: row-start addresses + per-cell values.

    The overlay reserves ``row_header_w`` pixels on the left for the row labels
    (DMX start address of each row: 1, 33, 65, …, 481) and lays out the 32×16
    cells in the remaining width. Cells are transparent so the GL heatmap shows
    through; only the white digit glyphs and the dim gutter background paint.
    """
    img = Image.new("RGBA", (max(1, overlay_w), max(1, overlay_h)), (0, 0, 0, 0))
    draw = ImageDraw.Draw(img)

    # Dim background strip behind the row labels so the text stays readable
    # regardless of what's happening on the GL heatmap behind it.
    if row_header_w > 0:
        draw.rectangle(
            [(0, 0), (row_header_w - 1, overlay_h - 1)],
            fill=(10, 12, 20, 220),
        )

    grid_w_px = max(1, overlay_w - row_header_w)
    cell_w = grid_w_px / float(GRID_W)
    cell_h = overlay_h / float(GRID_H)

    # Per-cell value font: target ~55% of cell height, clamped so 3 digits
    # still fit horizontally inside one cell with a small padding.
    value_font_px = max(7, int(min(cell_h * 0.55, cell_w * 0.42)))
    value_font = _pick_font(value_font_px)

    # Row labels target the full row height; clamp to the gutter width too.
    row_font_px = max(8, int(min(cell_h * 0.50, row_header_w * 0.62)))
    row_font = _pick_font(row_font_px)

    for row in range(GRID_H):
        # DMX addresses are 1-based; row 0 starts at channel 1, row 1 at 33, etc.
        start_addr = row * GRID_W + 1
        if row_header_w > 0:
            draw.text(
                (row_header_w - max(2, row_header_w // 8), int((row + 0.5) * cell_h)),
                str(start_addr),
                font=row_font,
                fill=(190, 196, 220, 255),
                anchor="rm",
            )

        for col in range(GRID_W):
            idx = row * GRID_W + col
            if idx >= 512:
                break
            value = snapshot_512[idx] if idx < len(snapshot_512) else 0
            cx = row_header_w + (col + 0.5) * cell_w
            cy = (row + 0.5) * cell_h
            # Brighter values get darker text (yellow on bright BG would wash out);
            # dim cells get bright white text. The cutoff matches the cell's
            # luminance from _channel_rgb so digits stay legible across the ramp.
            ink = (16, 18, 28, 255) if value >= 170 else (244, 248, 255, 230)
            draw.text(
                (cx, cy),
                str(int(value)),
                font=value_font,
                fill=ink,
                anchor="mm",
            )

    # OpenGL expects first row = bottom of image for upload without UV flip.
    return img.transpose(Image.FLIP_TOP_BOTTOM)


@beartype
class DmxHeatmapRenderer:
    """Renders a single-universe DMX snapshot to an offscreen RGB framebuffer."""

    def __init__(self) -> None:
        self._ctx: mgl.Context | None = None
        self._prog: mgl.Program | None = None
        self._header_prog: mgl.Program | None = None
        self._overlay_prog: mgl.Program | None = None
        self._vao: mgl.VertexArray | None = None
        self._header_vao: mgl.VertexArray | None = None
        self._overlay_vao: mgl.VertexArray | None = None
        self._vbo: mgl.Buffer | None = None
        self._header_vbo: mgl.Buffer | None = None
        self._overlay_vbo: mgl.Buffer | None = None
        self._data_tex: mgl.Texture | None = None
        self._header_tex: mgl.Texture | None = None
        self._overlay_tex: mgl.Texture | None = None
        self._out_tex: mgl.Texture | None = None
        self._fbo: mgl.Framebuffer | None = None
        self._width = 0
        self._height = 0
        self._cached_header_key: tuple[int, int] | None = None
        # Cache key for the overlay texture: (overlay_w, overlay_h, row_header_w,
        # tuple(snapshot)). The overlay is expensive to redraw on the CPU so we
        # skip the rebuild whenever the DMX values haven't moved.
        self._cached_overlay_key: tuple[int, int, int, tuple[int, ...]] | None = None

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
        uniform vec3 bg_color;
        uniform float cell_gap;
        void main() {
            // Match PIL/header orientation: CPU row 0 is top of grid; GL v_uv.y=0 is bottom of quad.
            vec2 uv = vec2(v_uv.x, 1.0 - v_uv.y);
            vec2 cell = floor(uv * grid_size);
            vec2 f = fract(uv * grid_size);
            if (f.x < cell_gap || f.x > 1.0 - cell_gap || f.y < cell_gap || f.y > 1.0 - cell_gap) {
                out_color = bg_color;
            } else {
                vec2 center = (cell + 0.5) / grid_size;
                out_color = texture(data_tex, center).rgb;
            }
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
        # Alpha-blended overlay for per-cell DMX values + row-start address labels.
        overlay_fragment = """
        #version 330
        in vec2 v_uv;
        out vec4 out_color;
        uniform sampler2D overlay_tex;
        void main() {
            out_color = texture(overlay_tex, v_uv);
        }
        """
        self._overlay_prog = context.program(
            vertex_shader=vertex, fragment_shader=overlay_fragment
        )
        self._vbo = context.buffer(reserve=64)
        self._header_vbo = context.buffer(reserve=64)
        self._overlay_vbo = context.buffer(reserve=64)
        self._vao = context.vertex_array(
            self._prog, [(self._vbo, "2f 2f", "in_pos", "in_uv")]
        )
        self._header_vao = context.vertex_array(
            self._header_prog, [(self._header_vbo, "2f 2f", "in_pos", "in_uv")]
        )
        self._overlay_vao = context.vertex_array(
            self._overlay_prog, [(self._overlay_vbo, "2f 2f", "in_pos", "in_uv")]
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
        self._cached_overlay_key = None

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

    def _ensure_overlay_texture(
        self,
        context: mgl.Context,
        overlay_w: int,
        overlay_h: int,
        row_header_w: int,
        snapshot_512: list[int],
    ) -> None:
        """Build/upload the digits+row-headers RGBA overlay, skipping no-op rebuilds."""
        snapshot_key = tuple(snapshot_512[:512]) + (0,) * max(0, 512 - len(snapshot_512))
        key = (overlay_w, overlay_h, row_header_w, snapshot_key)
        if self._overlay_tex is not None and self._cached_overlay_key == key:
            return
        if self._overlay_tex is not None:
            self._overlay_tex.release()
        img = _build_overlay_rgba_image(overlay_w, overlay_h, row_header_w, snapshot_512)
        self._overlay_tex = context.texture((overlay_w, overlay_h), 4, data=img.tobytes())
        self._overlay_tex.filter = (mgl.LINEAR, mgl.LINEAR)
        self._cached_overlay_key = key

    def _write_quad_vbo(
        self, vbo: mgl.Buffer, x0: float, y0: float, x1: float, y1: float
    ) -> None:
        """Full UV 0..1 over the quad (triangle strip: BL, BR, TL, TR)."""
        verts = (x0, y0, 0.0, 0.0, x1, y0, 1.0, 0.0, x0, y1, 0.0, 1.0, x1, y1, 1.0, 1.0)
        vbo.write(struct.pack("16f", *verts))

    @staticmethod
    def _grid_quad_ndc_centered(y_split: float, scale: float) -> tuple[float, float, float, float]:
        """NDC bounds (x0, y0, x1, y1) for the heatmap, centered in [-1,1] × [-1, y_split]."""
        x_lo, x_hi = -1.0, 1.0
        y_lo, y_hi = -1.0, y_split
        cx = (x_lo + x_hi) * 0.5
        cy = (y_lo + y_hi) * 0.5
        half_w = (x_hi - x_lo) * 0.5 * scale
        half_h = (y_hi - y_lo) * 0.5 * scale
        return cx - half_w, cy - half_h, cx + half_w, cy + half_h

    def render(
        self, context: mgl.Context, snapshot_512: list[int], width: int, height: int
    ) -> mgl.Framebuffer | None:
        if (
            self._prog is None
            or self._vao is None
            or self._header_prog is None
            or self._overlay_prog is None
            or self._overlay_vao is None
        ):
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
        assert self._overlay_vbo is not None

        header_h = max(1, int(round(height * HEADER_HEIGHT_FRAC)))
        y_split = 1.0 - (2.0 * header_h / float(height))

        # Outer "heatmap area" NDC quad — includes the row-header gutter on the left.
        ax0, ay0, ax1, ay1 = self._grid_quad_ndc_centered(y_split, HEATMAP_NDC_SCALE)
        area_w_ndc = ax1 - ax0
        gutter_w_ndc = area_w_ndc * ROW_HEADER_WIDTH_FRAC

        # Heatmap cell-grid quad (no gutter) — what the GL cell shader paints.
        gx0 = ax0 + gutter_w_ndc
        gx1 = ax1
        gy0 = ay0
        gy1 = ay1
        self._write_quad_vbo(self._vbo, gx0, gy0, gx1, gy1)
        self._write_quad_vbo(self._header_vbo, -1.0, y_split, 1.0, 1.0)
        # Overlay covers the full heatmap area (gutter + cells).
        self._write_quad_vbo(self._overlay_vbo, ax0, ay0, ax1, ay1)

        # Pixel sizes drive the PIL overlay resolution (one texel per output pixel).
        area_w_px = max(1, int(round(0.5 * area_w_ndc * float(width))))
        area_h_px = max(1, int(round(0.5 * (ay1 - ay0) * float(height))))
        gutter_w_px = max(1, int(round(area_w_px * ROW_HEADER_WIDTH_FRAC)))

        self._ensure_header_texture(context, width, height)
        self._ensure_overlay_texture(
            context, area_w_px, area_h_px, gutter_w_px, snapshot_512
        )
        assert self._header_tex is not None
        assert self._overlay_tex is not None

        bg = (0.02, 0.02, 0.06)
        self._fbo.use()
        self._fbo.clear(*bg)

        self._data_tex.use(0)
        self._prog["data_tex"].value = 0
        self._prog["grid_size"].value = (float(GRID_W), float(GRID_H))
        self._prog["bg_color"].value = bg
        self._prog["cell_gap"].value = float(CELL_GAP_FRAC)
        self._vao.render(mgl.TRIANGLE_STRIP)

        self._header_tex.use(0)
        self._header_prog["header_tex"].value = 0
        self._header_vao.render(mgl.TRIANGLE_STRIP)

        # Per-cell DMX values + row-start labels, alpha-blended over the heatmap.
        context.enable(mgl.BLEND)
        context.blend_func = (mgl.SRC_ALPHA, mgl.ONE_MINUS_SRC_ALPHA)
        try:
            self._overlay_tex.use(0)
            self._overlay_prog["overlay_tex"].value = 0
            self._overlay_vao.render(mgl.TRIANGLE_STRIP)
        finally:
            context.disable(mgl.BLEND)
        return self._fbo
