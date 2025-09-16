#!/usr/bin/env python3

import pytest
import numpy as np
import moderngl as mgl

from parrot.vj.nodes.static_color import StaticColor, White, Red, Green, Blue, Gray
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode
from parrot.utils.colour import Color
from parrot.graph.BaseInterpretationNode import Vibe


class TestStaticColorGL:
    """Test StaticColor node with real OpenGL rendering"""

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

    def test_white_static_color(self, gl_context, color_scheme):
        """Test that White factory function renders white pixels"""
        white_node = White(width=128, height=128)

        white_node.enter(gl_context)

        try:
            frame = Frame({FrameSignal.freq_low: 0.0})

            result_framebuffer = white_node.render(frame, color_scheme, gl_context)

            # Read the framebuffer data
            fb_data = result_framebuffer.read()
            pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                (result_framebuffer.height, result_framebuffer.width, 3)
            )

            # All pixels should be white (255, 255, 255)
            expected_white = 255
            assert np.all(
                pixels == expected_white
            ), f"Expected white pixels (255), got min={np.min(pixels)}, max={np.max(pixels)}"

        finally:
            white_node.exit()

    def test_red_static_color(self, gl_context, color_scheme):
        """Test that Red factory function renders red pixels"""
        red_node = Red(width=128, height=128)

        red_node.enter(gl_context)

        try:
            frame = Frame({FrameSignal.freq_low: 0.0})

            result_framebuffer = red_node.render(frame, color_scheme, gl_context)

            # Read the framebuffer data
            fb_data = result_framebuffer.read()
            pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                (result_framebuffer.height, result_framebuffer.width, 3)
            )

            # Should be red (255, 0, 0)
            assert np.all(pixels[:, :, 0] == 255), "Red channel should be 255"
            assert np.all(pixels[:, :, 1] == 0), "Green channel should be 0"
            assert np.all(pixels[:, :, 2] == 0), "Blue channel should be 0"

        finally:
            red_node.exit()

    def test_green_static_color(self, gl_context, color_scheme):
        """Test that Green factory function renders green pixels"""
        green_node = Green(width=128, height=128)

        green_node.enter(gl_context)

        try:
            frame = Frame({FrameSignal.freq_low: 0.0})

            result_framebuffer = green_node.render(frame, color_scheme, gl_context)

            # Read the framebuffer data
            fb_data = result_framebuffer.read()
            pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                (result_framebuffer.height, result_framebuffer.width, 3)
            )

            # Should be green (0, 255, 0)
            assert np.all(pixels[:, :, 0] == 0), "Red channel should be 0"
            assert np.all(pixels[:, :, 1] == 255), "Green channel should be 255"
            assert np.all(pixels[:, :, 2] == 0), "Blue channel should be 0"

        finally:
            green_node.exit()

    def test_blue_static_color(self, gl_context, color_scheme):
        """Test that Blue factory function renders blue pixels"""
        blue_node = Blue(width=128, height=128)

        blue_node.enter(gl_context)

        try:
            frame = Frame({FrameSignal.freq_low: 0.0})

            result_framebuffer = blue_node.render(frame, color_scheme, gl_context)

            # Read the framebuffer data
            fb_data = result_framebuffer.read()
            pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                (result_framebuffer.height, result_framebuffer.width, 3)
            )

            # Should be blue (0, 0, 255)
            assert np.all(pixels[:, :, 0] == 0), "Red channel should be 0"
            assert np.all(pixels[:, :, 1] == 0), "Green channel should be 0"
            assert np.all(pixels[:, :, 2] == 255), "Blue channel should be 255"

        finally:
            blue_node.exit()

    def test_gray_static_color(self, gl_context, color_scheme):
        """Test that Gray factory function renders gray pixels"""
        gray_intensity = 0.5
        gray_node = Gray(intensity=gray_intensity, width=128, height=128)

        gray_node.enter(gl_context)

        try:
            frame = Frame({FrameSignal.freq_low: 0.0})

            result_framebuffer = gray_node.render(frame, color_scheme, gl_context)

            # Read the framebuffer data
            fb_data = result_framebuffer.read()
            pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                (result_framebuffer.height, result_framebuffer.width, 3)
            )

            # Should be gray with specified intensity
            expected_gray = int(255 * gray_intensity)
            tolerance = 2  # Allow small rounding differences

            assert np.all(
                np.abs(pixels[:, :, 0] - expected_gray) <= tolerance
            ), f"Red channel should be ~{expected_gray}"
            assert np.all(
                np.abs(pixels[:, :, 1] - expected_gray) <= tolerance
            ), f"Green channel should be ~{expected_gray}"
            assert np.all(
                np.abs(pixels[:, :, 2] - expected_gray) <= tolerance
            ), f"Blue channel should be ~{expected_gray}"

        finally:
            gray_node.exit()

    def test_custom_color(self, gl_context, color_scheme):
        """Test StaticColor with custom color values"""
        # Test purple color (0.5, 0.0, 1.0)
        purple_node = StaticColor(color=(0.5, 0.0, 1.0), width=64, height=64)

        purple_node.enter(gl_context)

        try:
            frame = Frame({FrameSignal.freq_low: 0.0})

            result_framebuffer = purple_node.render(frame, color_scheme, gl_context)

            # Read the framebuffer data
            fb_data = result_framebuffer.read()
            pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                (result_framebuffer.height, result_framebuffer.width, 3)
            )

            # Should be purple (127, 0, 255)
            tolerance = 2
            assert np.all(
                np.abs(pixels[:, :, 0] - 127) <= tolerance
            ), "Red channel should be ~127"
            assert np.all(pixels[:, :, 1] == 0), "Green channel should be 0"
            assert np.all(pixels[:, :, 2] == 255), "Blue channel should be 255"

        finally:
            purple_node.exit()

    def test_different_dimensions(self, gl_context, color_scheme):
        """Test StaticColor with different dimensions"""
        sizes = [(32, 32), (256, 128), (100, 200)]

        for width, height in sizes:
            white_node = White(width=width, height=height)

            white_node.enter(gl_context)

            try:
                frame = Frame({FrameSignal.freq_low: 0.0})

                result_framebuffer = white_node.render(frame, color_scheme, gl_context)

                # Check dimensions
                assert result_framebuffer.width == width
                assert result_framebuffer.height == height

                # Verify pixels are white
                fb_data = result_framebuffer.read()
                pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                    (height, width, 3)
                )

                assert np.all(
                    pixels == 255
                ), f"Size {width}x{height}: Expected white pixels"

            finally:
                white_node.exit()
