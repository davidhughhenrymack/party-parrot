#!/usr/bin/env python3

import numpy as np
import pytest
import moderngl as mgl
from PIL import Image

from parrot.vj.nodes.sparkle_field_effect import SparkleFieldEffect
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


def test_sparkle_field_renders_and_saves_png(gl_context, color_scheme, tmp_path):
    """Headless render under high signal: sparkles should be visible and bounded."""
    w, h = 640, 360
    fx = SparkleFieldEffect(width=w, height=h)
    fx.enter(gl_context)
    frame = Frame({s: 0.0 for s in FrameSignal})
    frame.extend(
        {
            FrameSignal.freq_high: 1.0,
            FrameSignal.pulse: 0.8,
            FrameSignal.strobe: 0.5,
        }
    )
    fbo = fx.render(frame, color_scheme, gl_context)
    assert fbo is not None
    tex = fbo.color_attachments[0]
    assert tex.size == (w, h)

    raw = tex.read()
    arr = np.frombuffer(raw, dtype=np.uint8).reshape(h, w, 3)
    mean_luma = float(np.mean(arr)) / 255.0
    assert 0.002 < mean_luma < 0.35, f"unexpected average brightness {mean_luma}"

    out = tmp_path / "sparkle_field.png"
    Image.fromarray(np.flipud(arr)).save(out)
    assert out.stat().st_size > 5000

    fx.exit()
