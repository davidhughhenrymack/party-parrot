#!/usr/bin/env python3

import pytest
import numpy as np
import moderngl as mgl

from parrot.vj.nodes.noise_effect import NoiseEffect
from parrot.vj.nodes.static_color import StaticColor
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode
from parrot.utils.colour import Color
from parrot.graph.BaseInterpretationNode import Vibe


class TestNoiseEffectGL:
    """Test NoiseEffect with real OpenGL rendering"""

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
    def blue_input_node(self):
        """Create a blue input node for testing noise effects"""
        return StaticColor(color=(0.2, 0.4, 0.9), width=128, height=128)  # Blue

    @pytest.fixture
    def color_scheme(self):
        """Create a color scheme"""
        return ColorScheme(
            fg=Color("red"), bg=Color("black"), bg_contrast=Color("white")
        )

    def test_noise_effect_no_signal(self, gl_context, blue_input_node, color_scheme):
        """Test noise effect with no audio signal (minimal noise)"""
        noise_node = NoiseEffect(
            blue_input_node,
            noise_intensity=0.3,
            noise_scale=100.0,
            static_lines=True,
            color_noise=True,
            signal=FrameSignal.sustained_high,
        )

        blue_input_node.enter(gl_context)
        noise_node.enter(gl_context)

        try:
            # Create frame with no signal
            frame = Frame({FrameSignal.sustained_high: 0.0})

            result_framebuffer = noise_node.render(frame, color_scheme, gl_context)

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

            # Should preserve some aspect of blue input (blue should be dominant)
            assert (
                blue_channel > red_channel
            ), "Blue should be higher than red (blue input)"
            assert (
                blue_channel > green_channel
            ), "Blue should be higher than green (blue input)"

        finally:
            noise_node.exit()
            blue_input_node.exit()

    def test_noise_effect_high_signal(self, gl_context, blue_input_node, color_scheme):
        """Test noise effect with high audio signal (more noise)"""
        noise_node = NoiseEffect(
            blue_input_node,
            noise_intensity=0.6,
            noise_scale=150.0,
            static_lines=True,
            color_noise=True,
            signal=FrameSignal.sustained_high,
        )

        blue_input_node.enter(gl_context)
        noise_node.enter(gl_context)

        try:
            # Create frame with high signal
            frame = Frame({FrameSignal.sustained_high: 1.0})

            result_framebuffer = noise_node.render(frame, color_scheme, gl_context)

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

            # Should have noise effects creating variation
            pixel_std = np.std(pixels)
            assert pixel_std > 3, "Should have pixel variation due to noise effects"

        finally:
            noise_node.exit()
            blue_input_node.exit()

    def test_noise_effect_progression(self, gl_context, blue_input_node, color_scheme):
        """Test noise effect with different signal levels"""
        noise_node = NoiseEffect(
            blue_input_node,
            noise_intensity=0.5,
            noise_scale=120.0,
            static_lines=True,
            color_noise=True,
            signal=FrameSignal.sustained_high,
        )

        blue_input_node.enter(gl_context)
        noise_node.enter(gl_context)

        try:
            signal_levels = [0.0, 0.3, 0.6, 1.0]
            variations = []

            for signal_level in signal_levels:
                frame = Frame({FrameSignal.sustained_high: signal_level})

                result_framebuffer = noise_node.render(frame, color_scheme, gl_context)

                fb_data = result_framebuffer.read()
                pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                    (result_framebuffer.height, result_framebuffer.width, 3)
                )

                # Calculate pixel variation as a measure of noise intensity
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

            # Should have some variation in noise intensity across signal levels
            variation_range = max(variations) - min(variations)
            assert (
                variation_range > 0.5
            ), "Should have variation in noise intensity across signal levels"

        finally:
            noise_node.exit()
            blue_input_node.exit()

    def test_noise_effect_different_colors(self, gl_context, color_scheme):
        """Test noise effect with different input colors"""
        colors_to_test = [
            ((1.0, 0.0, 0.0), "red"),
            ((0.0, 1.0, 0.0), "green"),
            ((0.0, 0.0, 1.0), "blue"),
            ((1.0, 1.0, 1.0), "white"),
            ((0.5, 0.5, 0.5), "gray"),
        ]

        for color, color_name in colors_to_test:
            input_node = StaticColor(color=color, width=64, height=64)
            noise_node = NoiseEffect(
                input_node,
                noise_intensity=0.4,
                noise_scale=100.0,
                signal=FrameSignal.sustained_high,
            )

            input_node.enter(gl_context)
            noise_node.enter(gl_context)

            try:
                # Test with medium signal
                frame = Frame({FrameSignal.sustained_high: 0.5})

                result_framebuffer = noise_node.render(frame, color_scheme, gl_context)

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
                    # All channels should be relatively high
                    assert all(
                        c > 100 for c in mean_rgb
                    ), "White should have high values in all channels"

            finally:
                noise_node.exit()
                input_node.exit()

    def test_noise_effect_size_adaptation(self, gl_context, color_scheme):
        """Test that noise effect adapts to different input sizes"""
        sizes = [(64, 64), (128, 256), (320, 240)]

        for width, height in sizes:
            blue_input = StaticColor(color=(0.2, 0.4, 0.9), width=width, height=height)
            noise_node = NoiseEffect(blue_input, signal=FrameSignal.sustained_high)

            blue_input.enter(gl_context)
            noise_node.enter(gl_context)

            try:
                frame = Frame({FrameSignal.sustained_high: 0.5})

                result_framebuffer = noise_node.render(frame, color_scheme, gl_context)

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
                noise_node.exit()
                blue_input.exit()

    def test_noise_effect_parameter_variations(
        self, gl_context, blue_input_node, color_scheme
    ):
        """Test noise effect with different parameter settings"""
        parameter_sets = [
            {
                "noise_intensity": 0.2,
                "noise_scale": 50.0,
                "static_lines": False,
                "color_noise": False,
            },  # Subtle
            {
                "noise_intensity": 0.4,
                "noise_scale": 100.0,
                "static_lines": True,
                "color_noise": True,
            },  # Medium
            {
                "noise_intensity": 0.7,
                "noise_scale": 200.0,
                "static_lines": True,
                "color_noise": True,
            },  # Intense
        ]

        blue_input_node.enter(gl_context)

        try:
            for i, params in enumerate(parameter_sets):
                noise_node = NoiseEffect(
                    blue_input_node,
                    noise_intensity=params["noise_intensity"],
                    noise_scale=params["noise_scale"],
                    static_lines=params["static_lines"],
                    color_noise=params["color_noise"],
                    signal=FrameSignal.sustained_high,
                )

                noise_node.enter(gl_context)

                try:
                    frame = Frame({FrameSignal.sustained_high: 0.7})
                    result_framebuffer = noise_node.render(
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

                    # Should have some variation (noise is working)
                    assert (
                        pixel_variation > 1
                    ), f"Parameter set {i}: Should have pixel variation"

                finally:
                    noise_node.exit()

        finally:
            blue_input_node.exit()

    def test_noise_effect_static_lines_comparison(
        self, gl_context, blue_input_node, color_scheme
    ):
        """Test difference between noise with and without static lines"""

        # Test without static lines
        no_lines_node = NoiseEffect(
            blue_input_node,
            noise_intensity=0.5,
            noise_scale=100.0,
            static_lines=False,
            color_noise=True,
            signal=FrameSignal.sustained_high,
        )

        # Test with static lines
        lines_node = NoiseEffect(
            blue_input_node,
            noise_intensity=0.5,
            noise_scale=100.0,
            static_lines=True,
            color_noise=True,
            signal=FrameSignal.sustained_high,
        )

        blue_input_node.enter(gl_context)

        try:
            frame = Frame({FrameSignal.sustained_high: 0.6})

            # Test without static lines
            no_lines_node.enter(gl_context)
            no_lines_result = no_lines_node.render(frame, color_scheme, gl_context)
            no_lines_pixels = np.frombuffer(
                no_lines_result.read(), dtype=np.uint8
            ).reshape((no_lines_result.height, no_lines_result.width, 3))
            no_lines_node.exit()

            # Test with static lines
            lines_node.enter(gl_context)
            lines_result = lines_node.render(frame, color_scheme, gl_context)
            lines_pixels = np.frombuffer(lines_result.read(), dtype=np.uint8).reshape(
                (lines_result.height, lines_result.width, 3)
            )
            lines_node.exit()

            # Both should produce valid output
            assert np.any(
                no_lines_pixels > 0
            ), "No static lines should produce non-black pixels"
            assert np.any(
                lines_pixels > 0
            ), "Static lines should produce non-black pixels"

            no_lines_variation = np.std(no_lines_pixels)
            lines_variation = np.std(lines_pixels)

            no_lines_mean = np.mean(no_lines_pixels, axis=(0, 1))
            lines_mean = np.mean(lines_pixels, axis=(0, 1))

            print(
                f"No static lines: variation={no_lines_variation:.2f}, mean RGB=({no_lines_mean[0]:.1f}, {no_lines_mean[1]:.1f}, {no_lines_mean[2]:.1f})"
            )
            print(
                f"Static lines: variation={lines_variation:.2f}, mean RGB=({lines_mean[0]:.1f}, {lines_mean[1]:.1f}, {lines_mean[2]:.1f})"
            )

            # Both should have some noise variation
            assert no_lines_variation > 1, "No static lines should have noise variation"
            assert lines_variation > 1, "Static lines should have noise variation"

        finally:
            blue_input_node.exit()

    def test_noise_effect_color_noise_comparison(
        self, gl_context, blue_input_node, color_scheme
    ):
        """Test difference between color noise and monochrome noise"""

        # Test without color noise (monochrome)
        mono_noise_node = NoiseEffect(
            blue_input_node,
            noise_intensity=0.5,
            noise_scale=100.0,
            static_lines=True,
            color_noise=False,
            signal=FrameSignal.sustained_high,
        )

        # Test with color noise
        color_noise_node = NoiseEffect(
            blue_input_node,
            noise_intensity=0.5,
            noise_scale=100.0,
            static_lines=True,
            color_noise=True,
            signal=FrameSignal.sustained_high,
        )

        blue_input_node.enter(gl_context)

        try:
            frame = Frame({FrameSignal.sustained_high: 0.6})

            # Test monochrome noise
            mono_noise_node.enter(gl_context)
            mono_result = mono_noise_node.render(frame, color_scheme, gl_context)
            mono_pixels = np.frombuffer(mono_result.read(), dtype=np.uint8).reshape(
                (mono_result.height, mono_result.width, 3)
            )
            mono_noise_node.exit()

            # Test color noise
            color_noise_node.enter(gl_context)
            color_result = color_noise_node.render(frame, color_scheme, gl_context)
            color_pixels = np.frombuffer(color_result.read(), dtype=np.uint8).reshape(
                (color_result.height, color_result.width, 3)
            )
            color_noise_node.exit()

            # Both should produce valid output
            assert np.any(
                mono_pixels > 0
            ), "Monochrome noise should produce non-black pixels"
            assert np.any(
                color_pixels > 0
            ), "Color noise should produce non-black pixels"

            mono_mean = np.mean(mono_pixels, axis=(0, 1))
            color_mean = np.mean(color_pixels, axis=(0, 1))

            print(
                f"Monochrome noise: mean RGB=({mono_mean[0]:.1f}, {mono_mean[1]:.1f}, {mono_mean[2]:.1f})"
            )
            print(
                f"Color noise: mean RGB=({color_mean[0]:.1f}, {color_mean[1]:.1f}, {color_mean[2]:.1f})"
            )

            # Both should preserve some blue dominance (blue input)
            assert (
                mono_mean[2] > mono_mean[0]
            ), "Monochrome noise should preserve blue dominance"
            assert (
                color_mean[2] > color_mean[0]
            ), "Color noise should preserve blue dominance"

        finally:
            blue_input_node.exit()

    def test_noise_effect_seed_variation(
        self, gl_context, blue_input_node, color_scheme
    ):
        """Test that noise effect produces different results with different seeds"""
        blue_input_node.enter(gl_context)

        try:
            results = []

            for i in range(3):
                noise_node = NoiseEffect(
                    blue_input_node,
                    noise_intensity=0.6,
                    noise_scale=120.0,
                    signal=FrameSignal.sustained_high,
                )

                noise_node.enter(gl_context)

                try:
                    # Generate different seeds
                    noise_node.generate(Vibe(Mode.rave))

                    frame = Frame({FrameSignal.sustained_high: 0.8})
                    result_framebuffer = noise_node.render(
                        frame, color_scheme, gl_context
                    )

                    fb_data = result_framebuffer.read()
                    pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                        (result_framebuffer.height, result_framebuffer.width, 3)
                    )

                    # Store result for comparison
                    results.append(np.mean(pixels, axis=(0, 1)))

                    assert np.any(pixels > 0), f"Seed {i}: Should have non-black pixels"

                finally:
                    noise_node.exit()

            # Results should show some variation (different seeds produce different outputs)
            result_variations = []
            for j in range(len(results[0])):  # For each RGB channel
                channel_values = [result[j] for result in results]
                variation = max(channel_values) - min(channel_values)
                result_variations.append(variation)

            total_variation = sum(result_variations)
            print(f"Seed variation test: total RGB variation = {total_variation:.2f}")

            # Should have some variation across different seeds (randomness is working)
            assert (
                total_variation > 0.5
            ), "Different seeds should produce some variation in output"

        finally:
            blue_input_node.exit()

    def test_noise_effect_scale_variations(
        self, gl_context, blue_input_node, color_scheme
    ):
        """Test noise effect with different noise scale settings"""
        noise_scales = [50.0, 100.0, 200.0, 400.0]  # From fine to coarse noise

        blue_input_node.enter(gl_context)

        try:
            for noise_scale in noise_scales:
                noise_node = NoiseEffect(
                    blue_input_node,
                    noise_intensity=0.5,
                    noise_scale=noise_scale,
                    static_lines=True,
                    color_noise=True,
                    signal=FrameSignal.sustained_high,
                )

                noise_node.enter(gl_context)

                try:
                    frame = Frame({FrameSignal.sustained_high: 0.6})
                    result_framebuffer = noise_node.render(
                        frame, color_scheme, gl_context
                    )

                    fb_data = result_framebuffer.read()
                    pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                        (result_framebuffer.height, result_framebuffer.width, 3)
                    )

                    # Should produce valid output
                    assert np.any(
                        pixels > 0
                    ), f"Noise scale {noise_scale}: Should have non-black pixels"

                    pixel_variation = np.std(pixels)
                    mean_rgb = np.mean(pixels, axis=(0, 1))

                    print(
                        f"Noise scale {noise_scale}: variation={pixel_variation:.2f}, mean RGB=({mean_rgb[0]:.1f}, {mean_rgb[1]:.1f}, {mean_rgb[2]:.1f})"
                    )

                    # Should have some noise variation
                    assert (
                        pixel_variation > 1
                    ), f"Noise scale {noise_scale}: Should have noise variation"

                finally:
                    noise_node.exit()

        finally:
            blue_input_node.exit()
