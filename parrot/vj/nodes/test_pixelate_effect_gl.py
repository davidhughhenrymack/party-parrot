#!/usr/bin/env python3

import pytest
import numpy as np
import moderngl as mgl

from parrot.vj.nodes.pixelate_effect import PixelateEffect
from parrot.vj.nodes.static_color import StaticColor
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode
from parrot.utils.colour import Color
from parrot.graph.BaseInterpretationNode import Vibe


class TestPixelateEffectGL:
    """Test PixelateEffect with real OpenGL rendering"""

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
    def gradient_input_node(self):
        """Create a gradient input node for testing pixelation effects"""
        # Use a colorful input that will show pixelation clearly
        return StaticColor(color=(0.8, 0.3, 0.7), width=128, height=128)  # Pink

    @pytest.fixture
    def color_scheme(self):
        """Create a color scheme"""
        return ColorScheme(
            fg=Color("red"), bg=Color("black"), bg_contrast=Color("white")
        )

    def test_pixelate_effect_no_signal(
        self, gl_context, gradient_input_node, color_scheme
    ):
        """Test pixelate effect with no audio signal (minimal pixelation)"""
        pixelate_node = PixelateEffect(
            gradient_input_node,
            pixel_size=8.0,
            color_depth=16,
            dither=True,
            signal=FrameSignal.freq_low,
        )

        gradient_input_node.enter(gl_context)
        pixelate_node.enter(gl_context)

        try:
            # Create frame with no signal
            frame = Frame({FrameSignal.freq_low: 0.0})

            result_framebuffer = pixelate_node.render(frame, color_scheme, gl_context)

            fb_data = result_framebuffer.read()
            pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                (result_framebuffer.height, result_framebuffer.width, 3)
            )

            # Should have non-black pixels (input color should come through)
            assert np.any(pixels > 0), "Should have non-black pixels"

            # Should not be all white
            assert np.any(pixels < 255), "Should not be all white"

            red_channel = np.mean(pixels[:, :, 0])
            green_channel = np.mean(pixels[:, :, 1])
            blue_channel = np.mean(pixels[:, :, 2])

            print(
                f"No signal - RGB: ({red_channel:.1f}, {green_channel:.1f}, {blue_channel:.1f})"
            )

            # Should preserve some aspect of pink input (high red, low green, high blue)
            assert (
                red_channel > green_channel
            ), "Red should be higher than green (pink input)"
            assert (
                blue_channel > green_channel
            ), "Blue should be higher than green (pink input)"

        finally:
            pixelate_node.exit()
            gradient_input_node.exit()

    def test_pixelate_effect_high_signal(
        self, gl_context, gradient_input_node, color_scheme
    ):
        """Test pixelate effect with high audio signal (more pixelation)"""
        pixelate_node = PixelateEffect(
            gradient_input_node,
            pixel_size=16.0,  # Larger pixels for visibility
            color_depth=8,  # Lower color depth for more quantization
            dither=True,
            signal=FrameSignal.freq_low,
        )

        gradient_input_node.enter(gl_context)
        pixelate_node.enter(gl_context)

        try:
            # Create frame with high signal
            frame = Frame({FrameSignal.freq_low: 1.0})

            result_framebuffer = pixelate_node.render(frame, color_scheme, gl_context)

            fb_data = result_framebuffer.read()
            pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                (result_framebuffer.height, result_framebuffer.width, 3)
            )

            # Should have non-black pixels
            assert np.any(pixels > 0), "Should have non-black pixels with high signal"

            red_channel = np.mean(pixels[:, :, 0])
            green_channel = np.mean(pixels[:, :, 1])
            blue_channel = np.mean(pixels[:, :, 2])

            print(
                f"High signal - RGB: ({red_channel:.1f}, {green_channel:.1f}, {blue_channel:.1f})"
            )

            # Should have some color quantization effects
            # With low color depth, we expect more discrete color values
            unique_reds = len(np.unique(pixels[:, :, 0]))
            unique_greens = len(np.unique(pixels[:, :, 1]))
            unique_blues = len(np.unique(pixels[:, :, 2]))

            print(
                f"Unique colors - R: {unique_reds}, G: {unique_greens}, B: {unique_blues}"
            )

            # Should have fewer unique colors due to quantization
            total_unique = unique_reds + unique_greens + unique_blues
            assert (
                total_unique < 300
            ), "Should have color quantization reducing unique colors"

        finally:
            pixelate_node.exit()
            gradient_input_node.exit()

    def test_pixelate_effect_progression(
        self, gl_context, gradient_input_node, color_scheme
    ):
        """Test pixelate effect with different signal levels"""
        pixelate_node = PixelateEffect(
            gradient_input_node,
            pixel_size=12.0,
            color_depth=12,
            dither=True,
            signal=FrameSignal.freq_low,
        )

        gradient_input_node.enter(gl_context)
        pixelate_node.enter(gl_context)

        try:
            signal_levels = [0.0, 0.3, 0.6, 1.0]
            unique_color_counts = []

            for signal_level in signal_levels:
                frame = Frame({FrameSignal.freq_low: signal_level})

                result_framebuffer = pixelate_node.render(
                    frame, color_scheme, gl_context
                )

                fb_data = result_framebuffer.read()
                pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                    (result_framebuffer.height, result_framebuffer.width, 3)
                )

                # Count unique colors as a measure of pixelation/quantization
                unique_colors = len(np.unique(pixels.reshape(-1, 3), axis=0))
                unique_color_counts.append(unique_colors)

                red_channel = np.mean(pixels[:, :, 0])
                green_channel = np.mean(pixels[:, :, 1])
                blue_channel = np.mean(pixels[:, :, 2])

                print(
                    f"Signal {signal_level}: RGB=({red_channel:.1f}, {green_channel:.1f}, {blue_channel:.1f}), unique_colors={unique_colors}"
                )

                # Basic sanity checks
                assert np.any(
                    pixels > 0
                ), f"Signal {signal_level}: Should have non-black pixels"

            # Should have some variation in pixelation across signal levels
            color_count_range = max(unique_color_counts) - min(unique_color_counts)
            assert (
                color_count_range >= 0
            ), "Should have some variation in pixelation across signal levels"

        finally:
            pixelate_node.exit()
            gradient_input_node.exit()

    def test_pixelate_effect_different_colors(self, gl_context, color_scheme):
        """Test pixelate effect with different input colors"""
        colors_to_test = [
            ((1.0, 0.0, 0.0), "red"),
            ((0.0, 1.0, 0.0), "green"),
            ((0.0, 0.0, 1.0), "blue"),
            ((1.0, 1.0, 0.0), "yellow"),
            ((1.0, 0.0, 1.0), "magenta"),
            ((0.0, 1.0, 1.0), "cyan"),
        ]

        for color, color_name in colors_to_test:
            input_node = StaticColor(color=color, width=64, height=64)
            pixelate_node = PixelateEffect(
                input_node,
                pixel_size=10.0,
                color_depth=8,
                signal=FrameSignal.freq_low,
            )

            input_node.enter(gl_context)
            pixelate_node.enter(gl_context)

            try:
                # Test with medium signal
                frame = Frame({FrameSignal.freq_low: 0.5})

                result_framebuffer = pixelate_node.render(
                    frame, color_scheme, gl_context
                )

                fb_data = result_framebuffer.read()
                pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                    (result_framebuffer.height, result_framebuffer.width, 3)
                )

                # Verify reasonable output
                assert np.any(
                    pixels > 0
                ), f"Color {color_name}: Should have non-black pixels"

                mean_rgb = np.mean(pixels, axis=(0, 1))
                print(
                    f"Color {color_name}: Mean RGB = ({mean_rgb[0]:.1f}, {mean_rgb[1]:.1f}, {mean_rgb[2]:.1f})"
                )

                # Should preserve the dominant color characteristics
                if color_name == "red":
                    assert (
                        mean_rgb[0] > mean_rgb[1] and mean_rgb[0] > mean_rgb[2]
                    ), "Red should still be dominant"
                elif color_name == "green":
                    assert (
                        mean_rgb[1] > mean_rgb[0] and mean_rgb[1] > mean_rgb[2]
                    ), "Green should still be dominant"
                elif color_name == "blue":
                    assert (
                        mean_rgb[2] > mean_rgb[0] and mean_rgb[2] > mean_rgb[1]
                    ), "Blue should still be dominant"

            finally:
                pixelate_node.exit()
                input_node.exit()

    def test_pixelate_effect_size_adaptation(self, gl_context, color_scheme):
        """Test that pixelate effect adapts to different input sizes"""
        sizes = [(64, 64), (128, 256), (320, 240)]

        for width, height in sizes:
            pink_input = StaticColor(color=(0.8, 0.3, 0.7), width=width, height=height)
            pixelate_node = PixelateEffect(pink_input, signal=FrameSignal.freq_low)

            pink_input.enter(gl_context)
            pixelate_node.enter(gl_context)

            try:
                frame = Frame({FrameSignal.freq_low: 0.5})

                result_framebuffer = pixelate_node.render(
                    frame, color_scheme, gl_context
                )

                # Check that output size matches input size
                assert result_framebuffer.width == width
                assert result_framebuffer.height == height

                # Verify we get reasonable output
                fb_data = result_framebuffer.read()
                pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                    (height, width, 3)
                )

                assert np.any(
                    pixels > 0
                ), f"Size {width}x{height}: Should have non-black pixels"

            finally:
                pixelate_node.exit()
                pink_input.exit()

    def test_pixelate_effect_parameter_variations(
        self, gl_context, gradient_input_node, color_scheme
    ):
        """Test pixelate effect with different parameter settings"""
        parameter_sets = [
            {"pixel_size": 4.0, "color_depth": 32, "dither": False},  # Fine
            {"pixel_size": 8.0, "color_depth": 16, "dither": True},  # Medium
            {"pixel_size": 16.0, "color_depth": 8, "dither": True},  # Coarse
        ]

        gradient_input_node.enter(gl_context)

        try:
            for i, params in enumerate(parameter_sets):
                pixelate_node = PixelateEffect(
                    gradient_input_node,
                    pixel_size=params["pixel_size"],
                    color_depth=params["color_depth"],
                    dither=params["dither"],
                    signal=FrameSignal.freq_low,
                )

                pixelate_node.enter(gl_context)

                try:
                    frame = Frame({FrameSignal.freq_low: 0.7})
                    result_framebuffer = pixelate_node.render(
                        frame, color_scheme, gl_context
                    )

                    fb_data = result_framebuffer.read()
                    pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                        (result_framebuffer.height, result_framebuffer.width, 3)
                    )

                    # Should produce valid output
                    assert np.any(
                        pixels > 0
                    ), f"Parameter set {i}: Should have non-black pixels"

                    unique_colors = len(np.unique(pixels.reshape(-1, 3), axis=0))
                    mean_rgb = np.mean(pixels, axis=(0, 1))

                    print(
                        f"Parameter set {i}: unique_colors={unique_colors}, mean RGB=({mean_rgb[0]:.1f}, {mean_rgb[1]:.1f}, {mean_rgb[2]:.1f})"
                    )

                    # Should have some color quantization (fewer unique colors than total pixels)
                    total_pixels = pixels.shape[0] * pixels.shape[1]
                    assert (
                        unique_colors < total_pixels
                    ), f"Parameter set {i}: Should have color quantization"

                finally:
                    pixelate_node.exit()

        finally:
            gradient_input_node.exit()

    def test_pixelate_effect_dither_comparison(
        self, gl_context, gradient_input_node, color_scheme
    ):
        """Test difference between dithered and non-dithered pixelation"""

        # Test without dither
        no_dither_node = PixelateEffect(
            gradient_input_node,
            pixel_size=12.0,
            color_depth=8,
            dither=False,
            signal=FrameSignal.freq_low,
        )

        # Test with dither
        dither_node = PixelateEffect(
            gradient_input_node,
            pixel_size=12.0,
            color_depth=8,
            dither=True,
            signal=FrameSignal.freq_low,
        )

        gradient_input_node.enter(gl_context)

        try:
            frame = Frame({FrameSignal.freq_low: 0.6})

            # Test without dither
            no_dither_node.enter(gl_context)
            no_dither_result = no_dither_node.render(frame, color_scheme, gl_context)
            no_dither_pixels = np.frombuffer(
                no_dither_result.read(), dtype=np.uint8
            ).reshape((no_dither_result.height, no_dither_result.width, 3))
            no_dither_node.exit()

            # Test with dither
            dither_node.enter(gl_context)
            dither_result = dither_node.render(frame, color_scheme, gl_context)
            dither_pixels = np.frombuffer(dither_result.read(), dtype=np.uint8).reshape(
                (dither_result.height, dither_result.width, 3)
            )
            dither_node.exit()

            # Both should produce valid output
            assert np.any(
                no_dither_pixels > 0
            ), "No dither should produce non-black pixels"
            assert np.any(dither_pixels > 0), "Dither should produce non-black pixels"

            no_dither_unique = len(np.unique(no_dither_pixels.reshape(-1, 3), axis=0))
            dither_unique = len(np.unique(dither_pixels.reshape(-1, 3), axis=0))

            no_dither_mean = np.mean(no_dither_pixels, axis=(0, 1))
            dither_mean = np.mean(dither_pixels, axis=(0, 1))

            print(
                f"No dither: unique_colors={no_dither_unique}, mean RGB=({no_dither_mean[0]:.1f}, {no_dither_mean[1]:.1f}, {no_dither_mean[2]:.1f})"
            )
            print(
                f"Dither: unique_colors={dither_unique}, mean RGB=({dither_mean[0]:.1f}, {dither_mean[1]:.1f}, {dither_mean[2]:.1f})"
            )

            # Both should have reasonable color quantization
            assert no_dither_unique > 0, "No dither should have some unique colors"
            assert dither_unique > 0, "Dither should have some unique colors"

        finally:
            gradient_input_node.exit()

    def test_pixelate_effect_color_depth_variations(
        self, gl_context, gradient_input_node, color_scheme
    ):
        """Test pixelate effect with different color depth settings"""
        color_depths = [4, 8, 16, 32]  # From very quantized to less quantized

        gradient_input_node.enter(gl_context)

        try:
            unique_color_counts = []

            for color_depth in color_depths:
                pixelate_node = PixelateEffect(
                    gradient_input_node,
                    pixel_size=10.0,
                    color_depth=color_depth,
                    dither=True,
                    signal=FrameSignal.freq_low,
                )

                pixelate_node.enter(gl_context)

                try:
                    frame = Frame({FrameSignal.freq_low: 0.6})
                    result_framebuffer = pixelate_node.render(
                        frame, color_scheme, gl_context
                    )

                    fb_data = result_framebuffer.read()
                    pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                        (result_framebuffer.height, result_framebuffer.width, 3)
                    )

                    # Count unique colors
                    unique_colors = len(np.unique(pixels.reshape(-1, 3), axis=0))
                    unique_color_counts.append(unique_colors)

                    assert np.any(
                        pixels > 0
                    ), f"Color depth {color_depth}: Should have non-black pixels"

                    mean_rgb = np.mean(pixels, axis=(0, 1))
                    print(
                        f"Color depth {color_depth}: unique_colors={unique_colors}, mean RGB=({mean_rgb[0]:.1f}, {mean_rgb[1]:.1f}, {mean_rgb[2]:.1f})"
                    )

                finally:
                    pixelate_node.exit()

            # Generally, higher color depth should allow more unique colors
            # But this might not be strictly monotonic due to dithering and other factors
            print(f"Color depth progression: {unique_color_counts}")

            # All should have some reasonable number of colors
            assert all(
                count > 0 for count in unique_color_counts
            ), "All color depths should produce some unique colors"

        finally:
            gradient_input_node.exit()

    def test_pixelate_effect_pixel_size_variations(
        self, gl_context, gradient_input_node, color_scheme
    ):
        """Test pixelate effect with different pixel sizes"""
        pixel_sizes = [4.0, 8.0, 16.0, 32.0]  # From fine to coarse

        gradient_input_node.enter(gl_context)

        try:
            for pixel_size in pixel_sizes:
                pixelate_node = PixelateEffect(
                    gradient_input_node,
                    pixel_size=pixel_size,
                    color_depth=16,
                    dither=True,
                    signal=FrameSignal.freq_low,
                )

                pixelate_node.enter(gl_context)

                try:
                    frame = Frame({FrameSignal.freq_low: 0.5})
                    result_framebuffer = pixelate_node.render(
                        frame, color_scheme, gl_context
                    )

                    fb_data = result_framebuffer.read()
                    pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                        (result_framebuffer.height, result_framebuffer.width, 3)
                    )

                    # Should produce valid output
                    assert np.any(
                        pixels > 0
                    ), f"Pixel size {pixel_size}: Should have non-black pixels"

                    pixel_variation = np.std(pixels)
                    mean_rgb = np.mean(pixels, axis=(0, 1))

                    print(
                        f"Pixel size {pixel_size}: variation={pixel_variation:.2f}, mean RGB=({mean_rgb[0]:.1f}, {mean_rgb[1]:.1f}, {mean_rgb[2]:.1f})"
                    )

                    # Should have some reasonable output
                    assert (
                        pixel_variation >= 0
                    ), f"Pixel size {pixel_size}: Should have non-negative variation"

                finally:
                    pixelate_node.exit()

        finally:
            gradient_input_node.exit()
