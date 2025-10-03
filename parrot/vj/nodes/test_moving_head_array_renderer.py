#!/usr/bin/env python3

import numpy as np
import moderngl as mgl
import pytest

from beartype import beartype

from parrot.director.color_scheme import ColorScheme
from parrot.director.frame import Frame, FrameSignal
from parrot.fixtures.moving_head import MovingHead
from parrot.graph.BaseInterpretationNode import BaseInterpretationNode
from parrot.utils.colour import Color
from parrot.vj.nodes.moving_head_array_renderer import (
    MovingHeadArrayRenderer,
    MovingHeadPlacement,
)


@beartype
class DummyNode(BaseInterpretationNode[mgl.Context, None, list[MovingHead]]):
    def __init__(self, fixtures: list[MovingHead]):
        super().__init__([])
        self.fixtures = fixtures
        self.render_calls = 0

    def render(self, frame: Frame, scheme: ColorScheme, context: mgl.Context):
        self.render_calls += 1
        return self.fixtures


@pytest.fixture
def gl_context():
    try:
        ctx = mgl.create_context(standalone=True, backend="egl")
    except Exception:
        try:
            ctx = mgl.create_context(standalone=True)
        except Exception as exc:
            pytest.skip(f"Cannot create headless OpenGL context: {exc}")
    yield ctx
    try:
        ctx.release()
    except Exception:
        pass


@pytest.fixture
def moving_head() -> MovingHead:
    return MovingHead(0, "test", 12, [])


@pytest.fixture
def placement() -> MovingHeadPlacement:
    return MovingHeadPlacement(
        position=np.array([0.0, 0.0, 0.0], dtype=np.float32),
        forward=np.array([0.0, 0.0, -1.0], dtype=np.float32),
    )


@pytest.fixture
def renderer(moving_head, placement):
    child = DummyNode([moving_head])
    renderer = MovingHeadArrayRenderer(
        child,
        placements=[placement],
        camera_eye=np.array([0.0, 0.0, 3.0], dtype=np.float32),
        camera_target=np.array([0.0, 0.0, 0.0], dtype=np.float32),
        camera_up=np.array([0.0, 1.0, 0.0], dtype=np.float32),
        width=64,
        height=64,
    )
    return renderer


@pytest.fixture
def frame() -> Frame:
    values = {signal: 0.0 for signal in FrameSignal}
    values[FrameSignal.freq_high] = 0.5
    return Frame(values)


@pytest.fixture
def scheme() -> ColorScheme:
    return ColorScheme(fg=Color("white"), bg=Color("black"), bg_contrast=Color("red"))


def test_beam_direction_defaults(renderer, moving_head, placement):
    direction = renderer._beam_direction(placement.forward, moving_head)
    np.testing.assert_allclose(direction, placement.forward, atol=1e-5)


def test_beam_direction_with_pan_tilt(renderer, moving_head):
    moving_head.set_pan_angle(90)
    moving_head.set_tilt_angle(45)
    base_forward = np.array([0.0, 0.0, -1.0], dtype=np.float32)
    direction = renderer._beam_direction(base_forward, moving_head)
    assert not np.allclose(direction, base_forward)
    assert np.linalg.norm(direction) - 1.0 < 1e-5


def test_render_calls_child(renderer, frame, scheme, gl_context):
    renderer.enter(gl_context)
    try:
        renderer.render(frame, scheme, gl_context)
        assert renderer.children[0].render_calls == 1
    finally:
        renderer.exit()
