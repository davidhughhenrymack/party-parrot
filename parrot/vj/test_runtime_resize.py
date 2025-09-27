import numpy as np
import pytest
import moderngl as mgl

from typing import Tuple

from parrot.vj.tkinter_vj_window import VJRenderer


class _FakeDirector:
    def __init__(self, src_w: int, src_h: int):
        self.src_w = src_w
        self.src_h = src_h
        self._fbo = None
        self._vao = None
        self._prog = None

    def setup(self, ctx: mgl.Context):
        # Create simple gradient shader
        vs = """
        #version 330 core
        in vec2 in_pos;
        out vec2 uv;
        void main(){
            gl_Position = vec4(in_pos, 0.0, 1.0);
            uv = (in_pos * 0.5) + 0.5;
        }
        """
        fs = """
        #version 330 core
        in vec2 uv;
        out vec3 color;
        void main(){
            color = vec3(uv.x, 0.0, 0.0);
        }
        """
        self._prog = ctx.program(vertex_shader=vs, fragment_shader=fs)
        quad = np.array(
            [
                -1.0,
                -1.0,
                1.0,
                -1.0,
                -1.0,
                1.0,
                1.0,
                1.0,
            ],
            dtype=np.float32,
        )
        vbo = ctx.buffer(quad.tobytes())
        self._vao = ctx.vertex_array(self._prog, [(vbo, "2f", "in_pos")])
        tex = ctx.texture((self.src_w, self.src_h), 3)
        self._fbo = ctx.framebuffer(color_attachments=[tex])

    def get_latest_frame_data(self) -> Tuple[object, object]:
        # Return non-None placeholders
        return object(), object()

    def render(self, ctx: mgl.Context, frame, scheme) -> mgl.Framebuffer:
        self._fbo.use()
        ctx.clear(0.0, 0.0, 0.0)
        self._vao.render(mgl.TRIANGLE_STRIP)
        return self._fbo

    def cleanup(self):
        pass


def _make_renderer_with_fake_director(src_w: int, src_h: int) -> VJRenderer:
    try:
        ctx = mgl.create_context(standalone=True, backend="egl")
    except Exception:
        try:
            ctx = mgl.create_context(standalone=True)
        except Exception as e:
            pytest.skip(f"Cannot create headless OpenGL context: {e}")

    director = _FakeDirector(src_w, src_h)
    renderer = VJRenderer(director, width=src_w, height=src_h)
    renderer.ctx = ctx
    director.setup(ctx)
    renderer._setup_display_pipeline()
    return renderer


def test_render_frame_resizes_smaller_then_larger():
    r = _make_renderer_with_fake_director(640, 360)

    # First small
    out = r.render_frame(256, 144)
    assert out is not None
    data, w, h = out
    assert (w, h) == (256, 144)

    # Then larger
    out2 = r.render_frame(512, 288)
    assert out2 is not None
    data2, w2, h2 = out2
    assert (w2, h2) == (512, 288)

    # Basic sanity on gradient mapping after resize
    img_small = np.frombuffer(data, dtype=np.uint8).reshape(144, 256, 3)
    img_large = np.frombuffer(data2, dtype=np.uint8).reshape(288, 512, 3)
    # Verify left edge red ~0, right edge red ~255
    assert int(img_small[:, 0, 0].mean()) <= 5
    assert int(img_small[:, -1, 0].mean()) >= 250
    assert int(img_large[:, 0, 0].mean()) <= 5
    assert int(img_large[:, -1, 0].mean()) >= 250
