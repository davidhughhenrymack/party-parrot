#!/usr/bin/env python3
"""Headless full-frame render: golden sparkles + Muro \"dmack\" (matches prom_dmack scene)."""

from __future__ import annotations

import os

import moderngl as mgl
import numpy as np
from PIL import Image

from parrot.graph.BaseInterpretationNode import Vibe
from parrot.director.frame import Frame, FrameSignal
from parrot.director.mode import Mode
from parrot.director.color_scheme import ColorScheme
from parrot.utils.colour import Color
from parrot.vj.nodes.layer_compose import LayerCompose, LayerSpec, BlendMode
from parrot.vj.nodes.sparkle_field_effect import SparkleFieldEffect
from parrot.vj.nodes.text_renderer import TextRenderer, muro_font_path


def render_prom_dmack_preview(
    out_name: str = "prom_dmack_full.png",
    width: int = 1920,
    height: int = 1080,
) -> str:
    ctx = mgl.create_context(standalone=True)

    orange = Color()
    orange.rgb = (1.0, 0.5, 0.0)
    black = Color()
    black.rgb = (0.0, 0.0, 0.0)
    blue = Color()
    blue.rgb = (0.0, 0.5, 1.0)
    scheme = ColorScheme(fg=orange, bg=black, bg_contrast=blue)
    frame = Frame({s: 0.0 for s in FrameSignal})

    sparkles = SparkleFieldEffect(width=width, height=height)
    title = TextRenderer(
        text="dmack",
        font_name="Muro",
        font_path=muro_font_path(),
        font_size=440,
        text_color=(255, 245, 200),
        bg_color=(0, 0, 0),
        width=width,
        height=height,
    )
    scene = LayerCompose(
        LayerSpec(sparkles, BlendMode.NORMAL),
        LayerSpec(title, BlendMode.SCREEN),
        width=width,
        height=height,
    )

    sparkles.enter(ctx)
    title.enter(ctx)
    scene.enter(ctx)
    scene.generate(Vibe(mode=Mode.rave))

    fbo = scene.render(frame, scheme, ctx)
    if fbo is None:
        raise RuntimeError("LayerCompose render returned None")

    data = fbo.read(components=3, dtype="f1")
    arr = np.frombuffer(data, dtype=np.uint8).reshape((height, width, 3))
    arr = np.flipud(arr)

    project_root = os.path.dirname(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    )
    out_dir = os.path.join(project_root, "test_output")
    os.makedirs(out_dir, exist_ok=True)
    out_path = os.path.join(out_dir, out_name)
    Image.fromarray(arr).save(out_path)

    scene.exit()
    title.exit()
    sparkles.exit()

    return out_path


if __name__ == "__main__":
    render_prom_dmack_preview()
