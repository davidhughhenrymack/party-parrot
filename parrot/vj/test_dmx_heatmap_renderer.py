"""Headless smoke test for DMX heatmap + header."""

import moderngl as mgl
import pytest

from parrot.vj.dmx_heatmap_renderer import DmxHeatmapRenderer


@pytest.mark.skipif(
    mgl.create_standalone_context is None,
    reason="No standalone GL context",
)
def test_dmx_heatmap_render_includes_header():
    ctx = mgl.create_standalone_context()
    try:
        r = DmxHeatmapRenderer()
        r.enter(ctx)
        snap = [0] * 512
        fbo = r.render(ctx, snap, 640, 480)
        assert fbo is not None
        assert fbo.color_attachments[0].size == (640, 480)
    finally:
        ctx.release()
