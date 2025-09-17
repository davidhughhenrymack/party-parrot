#!/usr/bin/env python3

import pytest
import numpy as np
import moderngl as mgl

from parrot.vj.nodes.datamosh_effect import DatamoshEffect
from parrot.vj.nodes.static_color import StaticColor
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode
from parrot.utils.colour import Color
from parrot.graph.BaseInterpretationNode import Vibe


class TestDatamoshEffectGL:
    """Test DatamoshEffect with real OpenGL rendering"""

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
        """Create a colorful input node for testing datamosh effects"""
        return StaticColor(color=(0.8, 0.4, 0.9), width=128, height=128)  # Purple

    @pytest.fixture
    def color_scheme(self):
        """Create a color scheme"""
        return ColorScheme(
            fg=Color("red"), bg=Color("black"), bg_contrast=Color("white")
        )

    def test_datamosh_effect_no_signal(
        self, gl_context, colorful_input_node, color_scheme
    ):
        """Test datamosh effect with no audio signal (minimal glitching)"""
        datamosh_node = DatamoshEffect(
            colorful_input_node,
            displacement_strength=0.05,
            corruption_intensity=0.3,
            glitch_frequency=0.8,
            signal=FrameSignal.freq_high,
        )

        colorful_input_node.enter(gl_context)
        datamosh_node.enter(gl_context)

        try:
            # Create frame with no signal
            frame = Frame({FrameSignal.freq_high: 0.0})

            result_framebuffer = datamosh_node.render(frame, color_scheme, gl_context)

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

            # Should have some color content (not pure black or white)
            assert red_channel > 10, "Should have some red content"
            assert blue_channel > 10, "Should have some blue content (purple input)"

        finally:
            datamosh_node.exit()
            colorful_input_node.exit()

    def test_datamosh_effect_high_signal(
        self, gl_context, colorful_input_node, color_scheme
    ):
        """Test datamosh effect with high audio signal (more glitching)"""
        datamosh_node = DatamoshEffect(
            colorful_input_node,
            displacement_strength=0.1,
            corruption_intensity=0.6,
            glitch_frequency=0.9,
            signal=FrameSignal.freq_high,
        )

        colorful_input_node.enter(gl_context)
        datamosh_node.enter(gl_context)

        try:
            # Create frame with high signal
            frame = Frame({FrameSignal.freq_high: 1.0})

            result_framebuffer = datamosh_node.render(frame, color_scheme, gl_context)

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

            # Should have some color variation due to glitch effects
            pixel_std = np.std(pixels)
            assert pixel_std > 1, "Should have pixel variation due to glitch effects"

        finally:
            datamosh_node.exit()
            colorful_input_node.exit()

    def test_datamosh_effect_progression(
        self, gl_context, colorful_input_node, color_scheme
    ):
        """Test datamosh effect with different signal levels"""
        datamosh_node = DatamoshEffect(
            colorful_input_node,
            displacement_strength=0.08,
            corruption_intensity=0.5,
            glitch_frequency=0.7,
            signal=FrameSignal.freq_high,
        )

        colorful_input_node.enter(gl_context)
        datamosh_node.enter(gl_context)

        try:
            signal_levels = [0.0, 0.3, 0.6, 1.0]
            variations = []

            for signal_level in signal_levels:
                frame = Frame({FrameSignal.freq_high: signal_level})

                result_framebuffer = datamosh_node.render(
                    frame, color_scheme, gl_context
                )

                fb_data = result_framebuffer.read()
                pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                    (result_framebuffer.height, result_framebuffer.width, 3)
                )

                # Calculate pixel variation as a measure of glitch intensity
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

            # Should have some variation in glitch intensity across signal levels
            variation_range = max(variations) - min(variations)
            assert (
                variation_range > 0.5
            ), "Should have variation in glitch intensity across signal levels"

        finally:
            datamosh_node.exit()
            colorful_input_node.exit()

    def test_datamosh_effect_different_colors(self, gl_context, color_scheme):
        """Test datamosh effect with different input colors"""
        colors_to_test = [
            ((1.0, 0.0, 0.0), "red"),
            ((0.0, 1.0, 0.0), "green"),
            ((0.0, 0.0, 1.0), "blue"),
            ((1.0, 1.0, 0.0), "yellow"),
            ((0.5, 0.5, 0.5), "gray"),
        ]

        for color, color_name in colors_to_test:
            input_node = StaticColor(color=color, width=64, height=64)
            datamosh_node = DatamoshEffect(
                input_node,
                displacement_strength=0.06,
                corruption_intensity=0.4,
                signal=FrameSignal.freq_high,
            )

            input_node.enter(gl_context)
            datamosh_node.enter(gl_context)

            try:
                # Test with medium signal
                frame = Frame({FrameSignal.freq_high: 0.5})

                result_framebuffer = datamosh_node.render(
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

            finally:
                datamosh_node.exit()
                input_node.exit()

    def test_datamosh_effect_size_adaptation(self, gl_context, color_scheme):
        """Test that datamosh effect adapts to different input sizes"""
        sizes = [(64, 64), (128, 256), (320, 240)]

        for width, height in sizes:
            purple_input = StaticColor(
                color=(0.8, 0.2, 0.9), width=width, height=height
            )
            datamosh_node = DatamoshEffect(purple_input, signal=FrameSignal.freq_high)

            purple_input.enter(gl_context)
            datamosh_node.enter(gl_context)

            try:
                frame = Frame({FrameSignal.freq_high: 0.5})

                result_framebuffer = datamosh_node.render(
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
                datamosh_node.exit()
                purple_input.exit()

    def test_datamosh_effect_parameter_variations(
        self, gl_context, colorful_input_node, color_scheme
    ):
        """Test datamosh effect with different parameter settings"""
        parameter_sets = [
            {
                "displacement_strength": 0.02,
                "corruption_intensity": 0.1,
                "glitch_frequency": 0.3,
            },  # Subtle
            {
                "displacement_strength": 0.05,
                "corruption_intensity": 0.3,
                "glitch_frequency": 0.6,
            },  # Medium
            {
                "displacement_strength": 0.1,
                "corruption_intensity": 0.7,
                "glitch_frequency": 0.9,
            },  # Intense
        ]

        colorful_input_node.enter(gl_context)

        try:
            for i, params in enumerate(parameter_sets):
                datamosh_node = DatamoshEffect(
                    colorful_input_node,
                    displacement_strength=params["displacement_strength"],
                    corruption_intensity=params["corruption_intensity"],
                    glitch_frequency=params["glitch_frequency"],
                    signal=FrameSignal.freq_high,
                )

                datamosh_node.enter(gl_context)

                try:
                    frame = Frame({FrameSignal.freq_high: 0.7})
                    result_framebuffer = datamosh_node.render(
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

                    # Should have some variation (effect is working)
                    assert (
                        pixel_variation > 0.5
                    ), f"Parameter set {i}: Should have pixel variation"

                finally:
                    datamosh_node.exit()

        finally:
            colorful_input_node.exit()

    def test_datamosh_effect_seed_variation(
        self, gl_context, colorful_input_node, color_scheme
    ):
        """Test that datamosh effect produces different results with different seeds"""
        colorful_input_node.enter(gl_context)

        try:
            results = []

            for i in range(3):
                datamosh_node = DatamoshEffect(
                    colorful_input_node,
                    displacement_strength=0.08,
                    corruption_intensity=0.5,
                    signal=FrameSignal.freq_high,
                )

                datamosh_node.enter(gl_context)

                try:
                    # Generate different seeds
                    datamosh_node.generate(Vibe(Mode.rave))

                    frame = Frame({FrameSignal.freq_high: 0.8})
                    result_framebuffer = datamosh_node.render(
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
                    datamosh_node.exit()

            # Results should show some variation (different seeds produce different outputs)
            result_variations = []
            for j in range(len(results[0])):  # For each RGB channel
                channel_values = [result[j] for result in results]
                variation = max(channel_values) - min(channel_values)
                result_variations.append(variation)

            total_variation = sum(result_variations)
            print(f"Seed variation test: total RGB variation = {total_variation:.2f}")

            # Should have some variation across different seeds (randomness is working)
            # Note: Variation might be subtle, so we use a lower threshold
            assert (
                total_variation > 0.1
            ), "Different seeds should produce some variation in output"

        finally:
            colorful_input_node.exit()
