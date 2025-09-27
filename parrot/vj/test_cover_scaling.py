import numpy as np
import pytest
import moderngl as mgl

from parrot.vj.tkinter_vj_window import VJRenderer


def _make_horizontal_gradient_rgb(width: int, height: int) -> bytes:
    # Red channel encodes normalized x (0..1), green/blue are zero
    x = np.linspace(0.0, 1.0, num=width, endpoint=True, dtype=np.float32)
    red_row = (x * 255.0).astype(np.uint8)
    row = np.stack([red_row, np.zeros_like(red_row), np.zeros_like(red_row)], axis=1)
    img = np.repeat(row[np.newaxis, :, :], height, axis=0)
    return img.tobytes()


@pytest.mark.parametrize(
    "src_w,src_h,tgt_w,tgt_h",
    [
        (300, 100, 200, 200),  # wider source, square target -> crop left/right
        (600, 200, 256, 256),  # another wider case
    ],
)
def test_vj_gpu_cover_scaling_horizontal_gradient(src_w, src_h, tgt_w, tgt_h):
    # Try EGL for headless first; fallback to default; skip if not available
    ctx = None
    try:
        ctx = mgl.create_context(standalone=True, backend="egl")
    except Exception:
        try:
            ctx = mgl.create_context(standalone=True)
        except Exception as e:
            pytest.skip(f"Cannot create headless OpenGL context: {e}")

    # Build VJ display pipeline in our context
    vjr = VJRenderer(vj_director=None, width=tgt_w, height=tgt_h)
    vjr.ctx = ctx
    vjr._setup_display_pipeline()
    vjr.update_display_size(tgt_w, tgt_h)
    assert vjr.display_framebuffer is not None

    # Prepare source texture with horizontal gradient in red channel
    gradient = _make_horizontal_gradient_rgb(src_w, src_h)
    src_tex = ctx.texture((src_w, src_h), 3, data=gradient)
    src_tex.filter = (mgl.NEAREST, mgl.NEAREST)
    src_tex.repeat_x = False
    src_tex.repeat_y = False

    # Render using the cover shader
    vjr.display_framebuffer.use()
    ctx.clear(0.0, 0.0, 0.0)
    src_tex.use(0)
    vjr.display_shader["source_texture"] = 0
    vjr.display_shader["source_size"].value = (float(src_w), float(src_h))
    vjr.display_shader["target_size"].value = (float(tgt_w), float(tgt_h))
    vjr.display_quad_vao.render(mgl.TRIANGLE_STRIP)

    # Read back pixels
    out_tex = vjr.display_framebuffer.color_attachments[0]
    buf = out_tex.read()
    img = np.frombuffer(buf, dtype=np.uint8).reshape(tgt_h, tgt_w, 3)

    # Expected mapping for cover when source is wider than target
    src_aspect = src_w / float(src_h)
    dst_aspect = tgt_w / float(tgt_h)
    assert src_aspect > dst_aspect  # by parametrization
    scale_x = src_aspect / dst_aspect

    def expected_red_at_x(x_pix: int) -> int:
        # Normalize x to [0,1]
        if tgt_w > 1:
            x_norm = x_pix / float(tgt_w - 1)
        else:
            x_norm = 0.0
        u = 0.5 + (x_norm - 0.5) / scale_x
        u = min(max(u, 0.0), 1.0)
        return int(round(u * 255.0))

    # Sample a few columns at multiple rows to verify full coverage (no letterbox)
    cols = [0, tgt_w // 2, max(0, tgt_w - 1)]
    rows = [0, tgt_h // 2, max(0, tgt_h - 1)]
    tol = 8  # allow small rounding differences

    for x in cols:
        exp_r = expected_red_at_x(x)
        for y in rows:
            r = int(img[y, x, 0])
            assert (
                abs(r - exp_r) <= tol
            ), f"red mismatch at (x={x}, y={y}): got {r}, expected {exp_r}"

    # Also assert green/blue near zero everywhere
    assert int(img[:, :, 1].max()) <= 1
    assert int(img[:, :, 2].max()) <= 1


def test_vj_gpu_cover_scaling_resizes_between_calls():
    # Establish headless context
    try:
        ctx = mgl.create_context(standalone=True, backend="egl")
    except Exception:
        try:
            ctx = mgl.create_context(standalone=True)
        except Exception as e:
            pytest.skip(f"Cannot create headless OpenGL context: {e}")

    # Source wider than both targets
    src_w, src_h = 640, 160
    large_w, large_h = 512, 256
    small_w, small_h = 256, 256  # shrink width, same height -> should shrink

    vjr = VJRenderer(vj_director=None, width=large_w, height=large_h)
    vjr.ctx = ctx
    vjr._setup_display_pipeline()

    # Prepare gradient source
    gradient = _make_horizontal_gradient_rgb(src_w, src_h)
    src_tex = ctx.texture((src_w, src_h), 3, data=gradient)
    src_tex.filter = (mgl.NEAREST, mgl.NEAREST)
    src_tex.repeat_x = False
    src_tex.repeat_y = False

    # First render at large target
    vjr.update_display_size(large_w, large_h)
    assert vjr.display_framebuffer is not None
    vjr.display_framebuffer.use()
    ctx.clear(0.0, 0.0, 0.0)
    src_tex.use(0)
    vjr.display_shader["source_texture"] = 0
    vjr.display_shader["source_size"].value = (float(src_w), float(src_h))
    vjr.display_shader["target_size"].value = (float(large_w), float(large_h))
    vjr.display_quad_vao.render(mgl.TRIANGLE_STRIP)
    large_tex = vjr.display_framebuffer.color_attachments[0]
    assert large_tex.size == (large_w, large_h)

    # Then render at smaller target (simulate GUI shrink)
    vjr.update_display_size(small_w, small_h)
    assert vjr.display_framebuffer is not None
    vjr.display_framebuffer.use()
    ctx.clear(0.0, 0.0, 0.0)
    vjr.display_shader["target_size"].value = (float(small_w), float(small_h))
    vjr.display_quad_vao.render(mgl.TRIANGLE_STRIP)
    small_tex = vjr.display_framebuffer.color_attachments[0]

    # Verify the framebuffer actually shrank and mapping still valid
    assert small_tex.size == (small_w, small_h)

    buf = small_tex.read()
    img = np.frombuffer(buf, dtype=np.uint8).reshape(small_h, small_w, 3)

    # Validate cover mapping still holds after resize
    src_aspect = src_w / float(src_h)
    dst_aspect = small_w / float(small_h)
    assert src_aspect > dst_aspect
    scale_x = src_aspect / dst_aspect

    def expected_red_at_x_small(x_pix: int) -> int:
        if small_w > 1:
            x_norm = x_pix / float(small_w - 1)
        else:
            x_norm = 0.0
        u = 0.5 + (x_norm - 0.5) / scale_x
        u = min(max(u, 0.0), 1.0)
        return int(round(u * 255.0))

    cols = [0, small_w // 2, max(0, small_w - 1)]
    rows = [0, small_h // 2, max(0, small_h - 1)]
    tol = 8
    for x in cols:
        exp_r = expected_red_at_x_small(x)
        for y in rows:
            r = int(img[y, x, 0])
            assert (
                abs(r - exp_r) <= tol
            ), f"after-resize red mismatch at (x={x}, y={y}): got {r}, expected {exp_r}"

    assert int(img[:, :, 1].max()) <= 1
    assert int(img[:, :, 2].max()) <= 1
