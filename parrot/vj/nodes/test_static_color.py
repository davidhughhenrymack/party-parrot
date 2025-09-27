#!/usr/bin/env python3

import pytest
import numpy as np
import moderngl as mgl
from unittest.mock import Mock

from parrot.vj.nodes.static_color import StaticColor, White, Red, Green, Blue, Gray
from parrot.vj.constants import DEFAULT_WIDTH, DEFAULT_HEIGHT
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode
from parrot.graph.BaseInterpretationNode import Vibe
from parrot.utils.colour import Color


class TestStaticColor:
    """Test the StaticColor node"""

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
            except Exception:
                pytest.skip("OpenGL context creation failed - no GPU/display available")

    @pytest.fixture
    def color_scheme(self):
        """Create a color scheme"""
        return ColorScheme(
            fg=Color("red"), bg=Color("black"), bg_contrast=Color("white")
        )

    @pytest.fixture
    def frame(self):
        """Create a basic frame"""
        return Frame({FrameSignal.freq_low: 0.5})

    def test_initialization_default(self):
        """Test StaticColor initialization with defaults"""
        node = StaticColor()

        assert node.color == (1.0, 1.0, 1.0)  # White
        assert node.width == DEFAULT_WIDTH
        assert node.height == DEFAULT_HEIGHT
        assert node.children == []

    def test_initialization_custom_color(self):
        """Test StaticColor initialization with custom color"""
        red_color = (1.0, 0.0, 0.0)
        node = StaticColor(color=red_color, width=512, height=512)

        assert node.color == red_color
        assert node.width == 512
        assert node.height == 512

    def test_initialization_custom_dimensions(self):
        """Test StaticColor initialization with custom dimensions"""
        node = StaticColor(width=1024, height=768)

        assert node.width == 1024
        assert node.height == 768

    def test_enter_exit_lifecycle(self, gl_context):
        """Test enter and exit methods"""
        node = StaticColor()

        # Test enter
        node.enter(gl_context)
        assert node.texture is not None
        assert node.framebuffer is not None
        assert node.shader_program is not None
        assert node.quad_vao is not None

        # Test exit
        node.exit()
        assert node.texture is None
        assert node.framebuffer is None
        assert node.shader_program is None
        assert node.quad_vao is None

    def test_generate(self):
        """Test generate method"""
        node = StaticColor()
        vibe = Vibe(Mode.rave)

        # Should not raise any errors
        node.generate(vibe)

    def test_render_white(self, gl_context, color_scheme, frame):
        """Test rendering white color"""
        node = StaticColor(color=(1.0, 1.0, 1.0), width=256, height=256)
        node.enter(gl_context)

        try:
            result_framebuffer = node.render(frame, color_scheme, gl_context)

            # Read pixels from the framebuffer
            pixels = np.frombuffer(result_framebuffer.read(), dtype=np.uint8).reshape(
                (256, 256, 3)
            )

            # Should be white (255, 255, 255)
            assert np.all(pixels == 255), "All pixels should be white (255)"

            print(f"✅ White render test: Mean brightness = {np.mean(pixels):.1f}")

        finally:
            node.exit()

    def test_render_red(self, gl_context, color_scheme, frame):
        """Test rendering red color"""
        node = StaticColor(color=(1.0, 0.0, 0.0), width=256, height=256)
        node.enter(gl_context)

        try:
            result_framebuffer = node.render(frame, color_scheme, gl_context)

            pixels = np.frombuffer(result_framebuffer.read(), dtype=np.uint8).reshape(
                (256, 256, 3)
            )

            # Should be red (255, 0, 0)
            assert np.all(pixels[:, :, 0] == 255), "Red channel should be 255"
            assert np.all(pixels[:, :, 1] == 0), "Green channel should be 0"
            assert np.all(pixels[:, :, 2] == 0), "Blue channel should be 0"

            print(
                f"✅ Red render test: R={np.mean(pixels[:,:,0]):.1f}, G={np.mean(pixels[:,:,1]):.1f}, B={np.mean(pixels[:,:,2]):.1f}"
            )

        finally:
            node.exit()

    def test_render_custom_color(self, gl_context, color_scheme, frame):
        """Test rendering custom color (purple)"""
        purple = (0.5, 0.0, 0.8)  # Purple-ish
        node = StaticColor(color=purple, width=256, height=256)
        node.enter(gl_context)

        try:
            result_framebuffer = node.render(frame, color_scheme, gl_context)

            pixels = np.frombuffer(result_framebuffer.read(), dtype=np.uint8).reshape(
                (256, 256, 3)
            )

            # Convert expected color to 0-255 range
            expected_r = int(purple[0] * 255)  # 127
            expected_g = int(purple[1] * 255)  # 0
            expected_b = int(purple[2] * 255)  # 204

            # Check color channels (with small tolerance for floating point)
            assert (
                abs(np.mean(pixels[:, :, 0]) - expected_r) < 2
            ), f"Red channel should be ~{expected_r}"
            assert (
                abs(np.mean(pixels[:, :, 1]) - expected_g) < 2
            ), f"Green channel should be ~{expected_g}"
            assert (
                abs(np.mean(pixels[:, :, 2]) - expected_b) < 2
            ), f"Blue channel should be ~{expected_b}"

            print(
                f"✅ Purple render test: Expected RGB({expected_r},{expected_g},{expected_b}), got RGB({np.mean(pixels[:,:,0]):.0f},{np.mean(pixels[:,:,1]):.0f},{np.mean(pixels[:,:,2]):.0f})"
            )

        finally:
            node.exit()

    def test_factory_functions(self):
        """Test convenience factory functions"""
        # Test White factory
        white_node = White(width=512, height=512)
        assert white_node.color == (1.0, 1.0, 1.0)
        assert white_node.width == 512
        assert white_node.height == 512

        # Test Red factory
        red_node = Red()
        assert red_node.color == (1.0, 0.0, 0.0)
        assert red_node.width == DEFAULT_WIDTH  # Default

        # Test Green factory
        green_node = Green()
        assert green_node.color == (0.0, 1.0, 0.0)

        # Test Blue factory
        blue_node = Blue()
        assert blue_node.color == (0.0, 0.0, 1.0)

        # Test Gray factory
        gray_node = Gray(intensity=0.7)
        assert gray_node.color == (0.7, 0.7, 0.7)

        # Test Gray factory with default intensity
        gray_default = Gray()
        assert gray_default.color == (0.5, 0.5, 0.5)

    def test_factory_functions_render(self, gl_context, color_scheme, frame):
        """Test that factory functions render correctly"""
        test_cases = [
            (Red(), (255, 0, 0), "Red"),
            (Green(), (0, 255, 0), "Green"),
            (Blue(), (0, 0, 255), "Blue"),
            (Gray(0.3), (76, 76, 76), "Gray 30%"),
        ]

        for node, expected_rgb, name in test_cases:
            node.enter(gl_context)

            try:
                result_framebuffer = node.render(frame, color_scheme, gl_context)

                # Use actual framebuffer dimensions
                data = result_framebuffer.read()
                pixels = np.frombuffer(data, dtype=np.uint8).reshape(
                    (result_framebuffer.height, result_framebuffer.width, 3)
                )

                # Check each color channel
                for i, expected_val in enumerate(expected_rgb):
                    actual_val = np.mean(pixels[:, :, i])
                    assert (
                        abs(actual_val - expected_val) < 2
                    ), f"{name} channel {i}: expected {expected_val}, got {actual_val:.0f}"

                print(
                    f"✅ {name} factory test: Expected RGB{expected_rgb}, got RGB({np.mean(pixels[:,:,0]):.0f},{np.mean(pixels[:,:,1]):.0f},{np.mean(pixels[:,:,2]):.0f})"
                )

            finally:
                node.exit()

    def test_different_dimensions(self, gl_context, color_scheme, frame):
        """Test rendering with different dimensions"""
        dimensions = [(128, 128), (512, 256), (1024, 768)]

        for width, height in dimensions:
            node = StaticColor(color=(0.8, 0.2, 0.6), width=width, height=height)
            node.enter(gl_context)

            try:
                result_framebuffer = node.render(frame, color_scheme, gl_context)

                # Verify framebuffer has correct dimensions
                assert result_framebuffer.width == width
                assert result_framebuffer.height == height

                pixels = np.frombuffer(
                    result_framebuffer.read(), dtype=np.uint8
                ).reshape((height, width, 3))

                # Verify all pixels have the expected color
                expected_r = int(0.8 * 255)  # 204
                expected_g = int(0.2 * 255)  # 51
                expected_b = int(0.6 * 255)  # 153

                assert abs(np.mean(pixels[:, :, 0]) - expected_r) < 2
                assert abs(np.mean(pixels[:, :, 1]) - expected_g) < 2
                assert abs(np.mean(pixels[:, :, 2]) - expected_b) < 2

                print(f"✅ Dimensions {width}x{height} test passed")

            finally:
                node.exit()

    def test_color_edge_cases(self):
        """Test edge cases for color values"""
        # Test black (all zeros)
        black_node = StaticColor(color=(0.0, 0.0, 0.0))
        assert black_node.color == (0.0, 0.0, 0.0)

        # Test partial colors
        partial_node = StaticColor(color=(0.25, 0.75, 1.0))
        assert partial_node.color == (0.25, 0.75, 1.0)

        # Test that colors are stored as provided (no clamping in constructor)
        over_node = StaticColor(
            color=(1.5, -0.1, 0.5)
        )  # Invalid range, but should be stored
        assert over_node.color == (1.5, -0.1, 0.5)
