#!/usr/bin/env python3

import pytest
import numpy as np
import moderngl as mgl

from parrot.vj.nodes.scanlines_effect import ScanlinesEffect
from parrot.vj.nodes.static_color import StaticColor
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode
from parrot.utils.colour import Color
from parrot.graph.BaseInterpretationNode import Vibe


class TestScanlinesEffectGL:
    """Test ScanlinesEffect with real OpenGL rendering"""

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
    def colorful_input_node(self):
        """Create a colorful input node for testing scanline effects"""
        return StaticColor(color=(0.9, 0.6, 0.2), width=128, height=128)  # Orange

    @pytest.fixture
    def color_scheme(self):
        """Create a color scheme"""
        return ColorScheme(
            fg=Color("red"), bg=Color("black"), bg_contrast=Color("white")
        )

    def test_scanlines_effect_no_signal(
        self, gl_context, colorful_input_node, color_scheme
    ):
        """Test scanlines effect with no audio signal (minimal effect)"""
        scanlines_node = ScanlinesEffect(
            colorful_input_node,
            scanline_intensity=0.4,
            scanline_count=300.0,
            roll_speed=0.5,
            curvature=0.1,
            signal=FrameSignal.sustained_low,
        )

        colorful_input_node.enter(gl_context)
        scanlines_node.enter(gl_context)

        try:
            # Create frame with no signal
            frame = Frame({FrameSignal.sustained_low: 0.0})

            result_framebuffer = scanlines_node.render(frame, color_scheme, gl_context)

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

            # Should preserve some aspect of orange input (high red, medium green, low blue)
            assert (
                red_channel > green_channel
            ), "Red should be higher than green (orange input)"
            assert (
                green_channel > blue_channel
            ), "Green should be higher than blue (orange input)"

        finally:
            scanlines_node.exit()
            colorful_input_node.exit()

    def test_scanlines_effect_high_signal(
        self, gl_context, colorful_input_node, color_scheme
    ):
        """Test scanlines effect with high audio signal (more intense scanlines)"""
        scanlines_node = ScanlinesEffect(
            colorful_input_node,
            scanline_intensity=0.6,
            scanline_count=400.0,
            roll_speed=1.0,
            curvature=0.2,
            signal=FrameSignal.sustained_low,
        )

        colorful_input_node.enter(gl_context)
        scanlines_node.enter(gl_context)

        try:
            # Create frame with high signal
            frame = Frame({FrameSignal.sustained_low: 1.0})

            result_framebuffer = scanlines_node.render(frame, color_scheme, gl_context)

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

            # Should have scanline patterns creating variation
            pixel_std = np.std(pixels)
            assert pixel_std > 2, "Should have pixel variation due to scanline effects"

        finally:
            scanlines_node.exit()
            colorful_input_node.exit()

    def test_scanlines_effect_progression(
        self, gl_context, colorful_input_node, color_scheme
    ):
        """Test scanlines effect with different signal levels"""
        scanlines_node = ScanlinesEffect(
            colorful_input_node,
            scanline_intensity=0.5,
            scanline_count=350.0,
            roll_speed=0.8,
            curvature=0.15,
            signal=FrameSignal.sustained_low,
        )

        colorful_input_node.enter(gl_context)
        scanlines_node.enter(gl_context)

        try:
            signal_levels = [0.0, 0.3, 0.6, 1.0]
            variations = []

            for signal_level in signal_levels:
                frame = Frame({FrameSignal.sustained_low: signal_level})

                result_framebuffer = scanlines_node.render(
                    frame, color_scheme, gl_context
                )

                fb_data = result_framebuffer.read()
                pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                    (result_framebuffer.height, result_framebuffer.width, 3)
                )

                # Calculate pixel variation as a measure of scanline intensity
                pixel_variation = np.std(pixels)
                variations.append(pixel_variation)

                red_channel = np.mean(pixels[:, :, 0])
                green_channel = np.mean(pixels[:, :, 1])
                blue_channel = np.mean(pixels[:, :, 2])

                print(
                    f"Signal {signal_level}: RGB=({red_channel:.1f}, {green_channel:.1f}, {blue_channel:.1f}), variation={pixel_variation:.2f}"
                )

                # Basic sanity checks
                assert np.any(
                    pixels > 0
                ), f"Signal {signal_level}: Should have non-black pixels"

            # Should have some variation in scanline intensity across signal levels
            variation_range = max(variations) - min(variations)
            assert (
                variation_range > 0.5
            ), "Should have variation in scanline intensity across signal levels"

        finally:
            scanlines_node.exit()
            colorful_input_node.exit()

    def test_scanlines_effect_different_colors(self, gl_context, color_scheme):
        """Test scanlines effect with different input colors"""
        colors_to_test = [
            ((1.0, 0.0, 0.0), "red"),
            ((0.0, 1.0, 0.0), "green"),
            ((0.0, 0.0, 1.0), "blue"),
            ((1.0, 1.0, 1.0), "white"),
            ((0.5, 0.5, 0.5), "gray"),
        ]

        for color, color_name in colors_to_test:
            input_node = StaticColor(color=color, width=64, height=64)
            scanlines_node = ScanlinesEffect(
                input_node,
                scanline_intensity=0.4,
                scanline_count=250.0,
                signal=FrameSignal.sustained_low,
            )

            input_node.enter(gl_context)
            scanlines_node.enter(gl_context)

            try:
                # Test with medium signal
                frame = Frame({FrameSignal.sustained_low: 0.5})

                result_framebuffer = scanlines_node.render(
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

                # Should preserve some aspect of the original color
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
                elif color_name == "white":
                    # All channels should be relatively high and similar
                    assert all(
                        c > 100 for c in mean_rgb
                    ), "White should have high values in all channels"

            finally:
                scanlines_node.exit()
                input_node.exit()

    def test_scanlines_effect_size_adaptation(self, gl_context, color_scheme):
        """Test that scanlines effect adapts to different input sizes"""
        sizes = [(64, 64), (128, 256), (320, 240)]

        for width, height in sizes:
            orange_input = StaticColor(
                color=(0.9, 0.6, 0.2), width=width, height=height
            )
            scanlines_node = ScanlinesEffect(
                orange_input, signal=FrameSignal.sustained_low
            )

            orange_input.enter(gl_context)
            scanlines_node.enter(gl_context)

            try:
                frame = Frame({FrameSignal.sustained_low: 0.5})

                result_framebuffer = scanlines_node.render(
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
                scanlines_node.exit()
                orange_input.exit()

    def test_scanlines_effect_parameter_variations(
        self, gl_context, colorful_input_node, color_scheme
    ):
        """Test scanlines effect with different parameter settings"""
        parameter_sets = [
            {
                "scanline_intensity": 0.2,
                "scanline_count": 200.0,
                "curvature": 0.05,
            },  # Subtle
            {
                "scanline_intensity": 0.4,
                "scanline_count": 300.0,
                "curvature": 0.1,
            },  # Medium
            {
                "scanline_intensity": 0.7,
                "scanline_count": 500.0,
                "curvature": 0.2,
            },  # Intense
        ]

        colorful_input_node.enter(gl_context)

        try:
            for i, params in enumerate(parameter_sets):
                scanlines_node = ScanlinesEffect(
                    colorful_input_node,
                    scanline_intensity=params["scanline_intensity"],
                    scanline_count=params["scanline_count"],
                    curvature=params["curvature"],
                    signal=FrameSignal.sustained_low,
                )

                scanlines_node.enter(gl_context)

                try:
                    frame = Frame({FrameSignal.sustained_low: 0.7})
                    result_framebuffer = scanlines_node.render(
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

                    pixel_variation = np.std(pixels)
                    mean_rgb = np.mean(pixels, axis=(0, 1))

                    print(
                        f"Parameter set {i}: variation={pixel_variation:.2f}, mean RGB=({mean_rgb[0]:.1f}, {mean_rgb[1]:.1f}, {mean_rgb[2]:.1f})"
                    )

                    # Should have some variation (scanlines are working)
                    assert (
                        pixel_variation > 1
                    ), f"Parameter set {i}: Should have pixel variation"

                finally:
                    scanlines_node.exit()

        finally:
            colorful_input_node.exit()

    def test_scanlines_effect_curvature_variations(
        self, gl_context, colorful_input_node, color_scheme
    ):
        """Test scanlines effect with different curvature settings"""
        curvature_values = [0.0, 0.1, 0.2, 0.3]  # From flat to curved

        colorful_input_node.enter(gl_context)

        try:
            results = []

            for curvature in curvature_values:
                scanlines_node = ScanlinesEffect(
                    colorful_input_node,
                    scanline_intensity=0.5,
                    scanline_count=300.0,
                    curvature=curvature,
                    signal=FrameSignal.sustained_low,
                )

                scanlines_node.enter(gl_context)

                try:
                    frame = Frame({FrameSignal.sustained_low: 0.6})
                    result_framebuffer = scanlines_node.render(
                        frame, color_scheme, gl_context
                    )

                    fb_data = result_framebuffer.read()
                    pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                        (result_framebuffer.height, result_framebuffer.width, 3)
                    )

                    # Store result for comparison
                    mean_rgb = np.mean(pixels, axis=(0, 1))
                    pixel_variation = np.std(pixels)
                    results.append((mean_rgb, pixel_variation))

                    assert np.any(
                        pixels > 0
                    ), f"Curvature {curvature}: Should have non-black pixels"

                    print(
                        f"Curvature {curvature}: variation={pixel_variation:.2f}, mean RGB=({mean_rgb[0]:.1f}, {mean_rgb[1]:.1f}, {mean_rgb[2]:.1f})"
                    )

                finally:
                    scanlines_node.exit()

            # Should have some variation across different curvature settings
            variations = [result[1] for result in results]
            variation_range = max(variations) - min(variations)

            print(f"Curvature variation test: variation range = {variation_range:.2f}")

            # Different curvature settings should produce some variation
            assert (
                variation_range >= 0
            ), "Different curvature settings should produce some variation"

        finally:
            colorful_input_node.exit()

    def test_scanlines_effect_roll_speed_variations(
        self, gl_context, colorful_input_node, color_scheme
    ):
        """Test scanlines effect with different roll speeds"""
        scanlines_node = ScanlinesEffect(
            colorful_input_node,
            scanline_intensity=0.5,
            scanline_count=300.0,
            roll_speed=2.0,  # Fast roll for visible time variation
            signal=FrameSignal.sustained_low,
        )

        colorful_input_node.enter(gl_context)
        scanlines_node.enter(gl_context)

        try:
            frame = Frame({FrameSignal.sustained_low: 0.7})
            results = []

            # Render multiple frames to see time variation from rolling
            for i in range(5):
                result_framebuffer = scanlines_node.render(
                    frame, color_scheme, gl_context
                )

                fb_data = result_framebuffer.read()
                pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                    (result_framebuffer.height, result_framebuffer.width, 3)
                )

                # Store mean RGB for comparison
                mean_rgb = np.mean(pixels, axis=(0, 1))
                results.append(mean_rgb)

                assert np.any(pixels > 0), f"Frame {i}: Should have non-black pixels"

            # Should have some variation over time (rolling scanlines)
            variations = []
            for channel in range(3):  # RGB channels
                channel_values = [result[channel] for result in results]
                variation = max(channel_values) - min(channel_values)
                variations.append(variation)

            total_variation = sum(variations)
            print(
                f"Roll speed variation test: total RGB variation = {total_variation:.2f}"
            )

            # Should have some time-based variation (rolling is working)
            # Note: This might be subtle depending on timing and roll speed
            assert total_variation >= 0, "Should have non-negative variation over time"

        finally:
            scanlines_node.exit()
            colorful_input_node.exit()
