#!/usr/bin/env python3

import numpy as np
import pytest
import moderngl as mgl
from PIL import Image

from parrot.vj.nodes.nyancat_background import NyancatBackground
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.utils.colour import Color


@pytest.fixture
def gl_context():
    try:
        return mgl.create_context(standalone=True)
    except Exception as exc:
        pytest.skip(f"Headless GL unavailable: {exc}")


@pytest.fixture
def color_scheme():
    orange = Color()
    orange.rgb = (1.0, 0.5, 0.0)
    black = Color()
    black.rgb = (0.0, 0.0, 0.0)
    blue = Color()
    blue.rgb = (0.0, 0.5, 1.0)
    return ColorScheme(fg=orange, bg=black, bg_contrast=blue)


def test_nyancat_background_renders_bright_scene(gl_context, color_scheme, tmp_path):
    """Shader draws a colorful sky + trail; mean luma should sit above near-black."""
    w, h = 640, 360
    fx = NyancatBackground(width=w, height=h)
    fx.enter(gl_context)
    frame = Frame({s: 0.35 for s in FrameSignal})
    fbo = fx.render(frame, color_scheme, gl_context)
    assert fbo is not None
    tex = fbo.color_attachments[0]
    assert tex.size == (w, h)

    raw = tex.read()
    arr = np.frombuffer(raw, dtype=np.uint8).reshape(h, w, 3)
    mean_luma = float(np.mean(arr)) / 255.0
    assert 0.02 < mean_luma < 0.95, f"unexpected average brightness {mean_luma}"

    out = tmp_path / "nyancat_bg.png"
    Image.fromarray(np.flipud(arr)).save(out)
    assert out.stat().st_size > 2000

    fx.exit()
