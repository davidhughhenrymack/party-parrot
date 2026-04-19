#!/usr/bin/env python3

import moderngl as mgl

from parrot.director.frame import Frame
from parrot.utils.colour import Color
from parrot.director.color_scheme import ColorScheme
from parrot.vj.nodes.circle_rainbow_background import CircleRainbowBackground


def test_circle_rainbow_compiles_and_renders_one_frame() -> None:
    ctx = mgl.create_standalone_context()
    node = CircleRainbowBackground(width=64, height=48)
    node.enter(ctx)
    frame = Frame({})
    scheme = ColorScheme(
        fg=Color("#FFFFFF"),
        bg=Color("#000000"),
        bg_contrast=Color("#FF0000"),
    )
    out = node.render(frame, scheme, ctx)
    assert out.width == 64
    assert out.height == 48
    node.exit()
    ctx.release()
