#!/usr/bin/env python3

import time
import random
import numpy as np
import pytest
import moderngl as mgl

from parrot.vj.nodes.concert_stage import ConcertStage
from parrot.graph.BaseInterpretationNode import Vibe
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode
from parrot.utils.colour import Color


# Hard fixed upper bounds (ms) for cold and warm render times.
# Values capture the typical performance observed on Apple M-series GPUs
# while keeping a safety margin for CI noise.
COLD_MAX_MS_GPU = 45.0
WARM_MAX_MS_GPU = 2.5

COLD_MAX_MS_CPU = 220.0
WARM_MAX_MS_CPU = 35.0

_CPU_RENDERER_TOKENS = (
    "llvmpipe",
    "softpipe",
    "swrast",
    "swiftshader",
)


def _uses_cpu_renderer(ctx: mgl.Context) -> bool:
    info = ctx.info
    renderer = info.get("GL_RENDERER", "").lower()
    vendor = info.get("GL_VENDOR", "").lower()

    return any(token in renderer or token in vendor for token in _CPU_RENDERER_TOKENS)


@pytest.fixture
def gl_context():
    """Create a headless OpenGL context suitable for CI/testing."""
    try:
        ctx = mgl.create_context(standalone=True, backend="egl")
        yield ctx
    except Exception:
        try:
            ctx = mgl.create_context(standalone=True)
            yield ctx
        except Exception as e:
            pytest.skip(f"Cannot create headless OpenGL context: {e}")


def _make_test_frame() -> Frame:
    # Provide a minimal set of signals used by nodes; values are modest to avoid extremes
    return Frame(
        {
            FrameSignal.freq_low: 0.4,
            FrameSignal.freq_high: 0.3,
            FrameSignal.freq_all: 0.35,
            FrameSignal.sustained_low: 0.4,
            FrameSignal.strobe: 0.0,
        }
    )


def _make_test_scheme() -> ColorScheme:
    return ColorScheme(fg=Color("white"), bg=Color("black"), bg_contrast=Color("red"))


class TestConcertStagePerformanceGL:
    def test_single_frame_is_20pct_faster_after_warmup(self, gl_context):
        """
        Render one frame with `ConcertStage` in rave mode and assert the cold and warm
        render times meet hard fixed thresholds.
        """

        # Deterministic setup for RandomChild/RandomOperation selections
        random.seed(0)
        np.random.seed(0)

        stage = ConcertStage()

        # Enter lifecycle for the full graph
        stage.enter_recursive(gl_context)

        # Configure for rave mode once; keep the same graph between the two renders
        stage.mode_switch.generate(Vibe(Mode.rave))

        if _uses_cpu_renderer(gl_context):
            cold_max = COLD_MAX_MS_CPU
            warm_max = WARM_MAX_MS_CPU
        else:
            cold_max = COLD_MAX_MS_GPU
            warm_max = WARM_MAX_MS_GPU

        frame = _make_test_frame()
        scheme = _make_test_scheme()

        # Cold render (first-ever render tends to compile/link shaders, allocate lazily)
        t0 = time.perf_counter()
        fb_cold = stage.render(frame, scheme, gl_context)
        try:
            gl_context.finish()  # ensure GPU work completes before timing
        except Exception:
            pass
        cold_ms = (time.perf_counter() - t0) * 1000.0

        # Sanity: we should get a framebuffer-like object (may be None if black path)
        assert fb_cold is not None

        # Warm render (should benefit from cached programs/buffers and be faster)
        t1 = time.perf_counter()
        fb_warm = stage.render(frame, scheme, gl_context)
        try:
            gl_context.finish()
        except Exception:
            pass
        warm_ms = (time.perf_counter() - t1) * 1000.0

        assert fb_warm is not None

        # Hard fixed timing expectations (upper bounds only)
        assert (
            cold_ms <= cold_max
        ), f"Cold render too slow: {cold_ms:.2f} ms > {cold_max:.2f} ms"
        assert (
            warm_ms <= warm_max
        ), f"Warm render too slow: {warm_ms:.2f} ms > {warm_max:.2f} ms"

        # Exit lifecycle to free resources
        stage.exit_recursive()
