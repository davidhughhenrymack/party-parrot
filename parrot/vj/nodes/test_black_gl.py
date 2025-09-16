#!/usr/bin/env python3

import pytest
import numpy as np
import moderngl as mgl

from parrot.vj.nodes.black import Black
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode
from parrot.utils.colour import Color
from parrot.graph.BaseInterpretationNode import Vibe


class TestBlackGL:
    """Test Black node with real OpenGL rendering"""

    @pytest.fixture
    def gl_context(self):
        """Create a real OpenGL context for testing"""
        try:
            # Create a headless OpenGL context
            context = mgl.create_context(standalone=True, backend="egl")
            yield context
        except Exception:
            # Fallback for systems without EGL
            try:
                context = mgl.create_context(standalone=True)
                yield context
            except Exception as e:
                raise RuntimeError(f"OpenGL context creation failed: {e}")

    @pytest.fixture
    def color_scheme(self):
        """Create a color scheme"""
        return ColorScheme(
            fg=Color("red"), bg=Color("black"), bg_contrast=Color("white")
        )

    def test_black_renders_black_pixels(self, gl_context, color_scheme):
        """Test that Black node renders all black pixels"""
        black_node = Black(width=256, height=256)

        black_node.enter(gl_context)

        try:
            frame = Frame({FrameSignal.freq_low: 0.0})

            result_framebuffer = black_node.render(frame, color_scheme, gl_context)

            # Read the framebuffer data
            fb_data = result_framebuffer.read()
            pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                (result_framebuffer.height, result_framebuffer.width, 3)
            )

            # All pixels should be black (0, 0, 0)
            assert np.all(
                pixels == 0
            ), f"Expected all black pixels, got min={np.min(pixels)}, max={np.max(pixels)}"

            # Check dimensions
            assert result_framebuffer.width == 256
            assert result_framebuffer.height == 256

        finally:
            black_node.exit()

    def test_black_different_sizes(self, gl_context, color_scheme):
        """Test Black node with different sizes"""
        sizes = [(128, 128), (512, 256), (1920, 1080)]

        for width, height in sizes:
            black_node = Black(width=width, height=height)

            black_node.enter(gl_context)

            try:
                frame = Frame({FrameSignal.freq_low: 0.0})

                result_framebuffer = black_node.render(frame, color_scheme, gl_context)

                # Check dimensions
                assert result_framebuffer.width == width
                assert result_framebuffer.height == height

                # Read and verify pixels are black
                fb_data = result_framebuffer.read()
                pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                    (height, width, 3)
                )

                assert np.all(
                    pixels == 0
                ), f"Size {width}x{height}: Expected all black pixels"

            finally:
                black_node.exit()

    def test_black_render_with_size(self, gl_context, color_scheme):
        """Test Black node's render_with_size method"""
        black_node = Black()

        black_node.enter(gl_context)

        try:
            frame = Frame({FrameSignal.freq_low: 0.0})

            # Test different sizes using render_with_size
            test_sizes = [(64, 64), (320, 240), (800, 600)]

            for width, height in test_sizes:
                result_framebuffer = black_node.render_with_size(
                    frame, color_scheme, gl_context, width, height
                )

                # Check dimensions
                assert result_framebuffer.width == width
                assert result_framebuffer.height == height

                # Verify pixels are black
                fb_data = result_framebuffer.read()
                pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                    (height, width, 3)
                )

                assert np.all(
                    pixels == 0
                ), f"Size {width}x{height}: Expected all black pixels"

        finally:
            black_node.exit()
