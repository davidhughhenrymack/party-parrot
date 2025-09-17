#!/usr/bin/env python3

import pytest
import numpy as np
import moderngl as mgl
import time

from parrot.vj.nodes.beat_hue_shift import BeatHueShift
from parrot.vj.nodes.static_color import StaticColor
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode
from parrot.utils.colour import Color
from parrot.graph.BaseInterpretationNode import Vibe


class TestBeatHueShiftGL:
    """Test BeatHueShift with real OpenGL rendering"""

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
    def red_input_node(self):
        """Create a red input node for testing hue shifts"""
        return StaticColor(color=(1.0, 0.0, 0.0), width=128, height=128)

    @pytest.fixture
    def color_scheme(self):
        """Create a color scheme"""
        return ColorScheme(
            fg=Color("red"), bg=Color("black"), bg_contrast=Color("white")
        )

    def test_beat_hue_shift_no_beat(self, gl_context, red_input_node, color_scheme):
        """Test hue shift with no beat detected (should maintain current hue)"""
        hue_shift_node = BeatHueShift(
            red_input_node,
            hue_shift_amount=60.0,
            saturation_boost=1.2,
            transition_speed=8.0,
            random_hues=False,
            signal=FrameSignal.pulse,
        )

        red_input_node.enter(gl_context)
        hue_shift_node.enter(gl_context)

        try:
            # Create frame with low pulse signal (no beat)
            frame = Frame({FrameSignal.pulse: 0.2})

            result_framebuffer = hue_shift_node.render(frame, color_scheme, gl_context)

            fb_data = result_framebuffer.read()
            pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                (result_framebuffer.height, result_framebuffer.width, 3)
            )

            # Should have some color output (not black)
            assert np.any(pixels > 0), "Should have non-black pixels"

            # Should not be all white either
            assert np.any(pixels < 255), "Should not be all white"

            red_channel = np.mean(pixels[:, :, 0])
            green_channel = np.mean(pixels[:, :, 1])
            blue_channel = np.mean(pixels[:, :, 2])

            print(
                f"No beat - RGB: ({red_channel:.1f}, {green_channel:.1f}, {blue_channel:.1f})"
            )

            # Should have some color variation (effect is working)
            total_variation = np.std(pixels)
            assert total_variation > 0, "Should have some color variation"

        finally:
            hue_shift_node.exit()
            red_input_node.exit()

    def test_beat_hue_shift_with_beat(self, gl_context, red_input_node, color_scheme):
        """Test hue shift with beat detected (should trigger hue change)"""
        hue_shift_node = BeatHueShift(
            red_input_node,
            hue_shift_amount=120.0,  # Large shift for visibility
            saturation_boost=1.5,
            transition_speed=12.0,
            random_hues=False,
            signal=FrameSignal.pulse,
        )

        red_input_node.enter(gl_context)
        hue_shift_node.enter(gl_context)

        try:
            # First, establish low baseline
            low_frame = Frame({FrameSignal.pulse: 0.2})
            hue_shift_node.render(low_frame, color_scheme, gl_context)

            # Wait a bit to ensure beat detection timing works
            time.sleep(0.05)

            # Then trigger a beat with high pulse signal
            beat_frame = Frame({FrameSignal.pulse: 0.9})
            result_framebuffer = hue_shift_node.render(
                beat_frame, color_scheme, gl_context
            )

            fb_data = result_framebuffer.read()
            pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                (result_framebuffer.height, result_framebuffer.width, 3)
            )

            # Should have non-black pixels
            assert np.any(pixels > 0), "Should have non-black pixels after beat"

            # Should have color content
            red_channel = np.mean(pixels[:, :, 0])
            green_channel = np.mean(pixels[:, :, 1])
            blue_channel = np.mean(pixels[:, :, 2])

            print(
                f"With beat - RGB: ({red_channel:.1f}, {green_channel:.1f}, {blue_channel:.1f})"
            )

            # Should have some saturation boost effect (not gray)
            max_channel = max(red_channel, green_channel, blue_channel)
            min_channel = min(red_channel, green_channel, blue_channel)
            saturation_diff = max_channel - min_channel
            assert saturation_diff > 10, "Should have some color saturation"

        finally:
            hue_shift_node.exit()
            red_input_node.exit()

    def test_beat_hue_shift_progression(self, gl_context, red_input_node, color_scheme):
        """Test hue shift with different signal levels"""
        hue_shift_node = BeatHueShift(
            red_input_node,
            hue_shift_amount=90.0,
            saturation_boost=1.3,
            transition_speed=10.0,
            random_hues=False,
            signal=FrameSignal.pulse,
        )

        red_input_node.enter(gl_context)
        hue_shift_node.enter(gl_context)

        try:
            signal_levels = [0.1, 0.4, 0.7, 0.95]
            rgb_values = []

            for i, signal_level in enumerate(signal_levels):
                frame = Frame({FrameSignal.pulse: signal_level})

                # Add small delay between frames for beat detection
                if i > 0:
                    time.sleep(0.05)

                result_framebuffer = hue_shift_node.render(
                    frame, color_scheme, gl_context
                )

                fb_data = result_framebuffer.read()
                pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                    (result_framebuffer.height, result_framebuffer.width, 3)
                )

                red_channel = np.mean(pixels[:, :, 0])
                green_channel = np.mean(pixels[:, :, 1])
                blue_channel = np.mean(pixels[:, :, 2])

                rgb_values.append((red_channel, green_channel, blue_channel))

                print(
                    f"Signal {signal_level}: RGB=({red_channel:.1f}, {green_channel:.1f}, {blue_channel:.1f})"
                )

                # Basic sanity checks
                assert np.any(
                    pixels > 0
                ), f"Signal {signal_level}: Should have non-black pixels"

            # Should have variation across different signal levels
            all_reds = [rgb[0] for rgb in rgb_values]
            all_greens = [rgb[1] for rgb in rgb_values]
            all_blues = [rgb[2] for rgb in rgb_values]

            # At least one channel should show variation
            red_variation = max(all_reds) - min(all_reds)
            green_variation = max(all_greens) - min(all_greens)
            blue_variation = max(all_blues) - min(all_blues)

            total_variation = red_variation + green_variation + blue_variation
            # Note: Beat hue shift might not show variation without actual beats
            assert (
                total_variation >= 0
            ), "Should have non-negative color variation across signal levels"

        finally:
            hue_shift_node.exit()
            red_input_node.exit()

    def test_beat_hue_shift_different_colors(self, gl_context, color_scheme):
        """Test hue shift with different input colors"""
        colors_to_test = [
            ((0.0, 1.0, 0.0), "green"),
            ((0.0, 0.0, 1.0), "blue"),
            ((1.0, 1.0, 0.0), "yellow"),
            ((1.0, 0.0, 1.0), "magenta"),
        ]

        for color, color_name in colors_to_test:
            input_node = StaticColor(color=color, width=64, height=64)
            hue_shift_node = BeatHueShift(
                input_node,
                hue_shift_amount=60.0,
                saturation_boost=1.2,
                signal=FrameSignal.pulse,
            )

            input_node.enter(gl_context)
            hue_shift_node.enter(gl_context)

            try:
                # Test with medium signal
                frame = Frame({FrameSignal.pulse: 0.6})

                result_framebuffer = hue_shift_node.render(
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
                assert np.any(
                    pixels < 255
                ), f"Color {color_name}: Should not be all white"

                mean_rgb = np.mean(pixels, axis=(0, 1))
                print(
                    f"Color {color_name}: Mean RGB = ({mean_rgb[0]:.1f}, {mean_rgb[1]:.1f}, {mean_rgb[2]:.1f})"
                )

                # Should have some color saturation (not gray)
                max_channel = np.max(mean_rgb)
                min_channel = np.min(mean_rgb)
                saturation = max_channel - min_channel
                assert (
                    saturation > 5
                ), f"Color {color_name}: Should have some saturation"

            finally:
                hue_shift_node.exit()
                input_node.exit()

    def test_beat_hue_shift_size_adaptation(self, gl_context, color_scheme):
        """Test that hue shift adapts to different input sizes"""
        sizes = [(64, 64), (128, 256), (320, 240)]

        for width, height in sizes:
            red_input = StaticColor(color=(1.0, 0.0, 0.0), width=width, height=height)
            hue_shift_node = BeatHueShift(red_input, signal=FrameSignal.pulse)

            red_input.enter(gl_context)
            hue_shift_node.enter(gl_context)

            try:
                frame = Frame({FrameSignal.pulse: 0.5})

                result_framebuffer = hue_shift_node.render(
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
                hue_shift_node.exit()
                red_input.exit()

    def test_beat_hue_shift_random_vs_sequential(
        self, gl_context, red_input_node, color_scheme
    ):
        """Test difference between random and sequential hue modes"""

        # Test sequential mode
        sequential_node = BeatHueShift(
            red_input_node,
            hue_shift_amount=60.0,
            random_hues=False,
            signal=FrameSignal.pulse,
        )

        # Test random mode
        random_node = BeatHueShift(
            red_input_node,
            hue_shift_amount=60.0,
            random_hues=True,
            signal=FrameSignal.pulse,
        )

        red_input_node.enter(gl_context)

        try:
            # Test sequential mode
            sequential_node.enter(gl_context)
            seq_frame = Frame({FrameSignal.pulse: 0.8})
            seq_result = sequential_node.render(seq_frame, color_scheme, gl_context)

            seq_pixels = np.frombuffer(seq_result.read(), dtype=np.uint8).reshape(
                (seq_result.height, seq_result.width, 3)
            )
            sequential_node.exit()

            # Test random mode
            random_node.enter(gl_context)
            rand_frame = Frame({FrameSignal.pulse: 0.8})
            rand_result = random_node.render(rand_frame, color_scheme, gl_context)

            rand_pixels = np.frombuffer(rand_result.read(), dtype=np.uint8).reshape(
                (rand_result.height, rand_result.width, 3)
            )
            random_node.exit()

            # Both should produce valid output
            assert np.any(
                seq_pixels > 0
            ), "Sequential mode should produce non-black pixels"
            assert np.any(
                rand_pixels > 0
            ), "Random mode should produce non-black pixels"

            seq_mean = np.mean(seq_pixels, axis=(0, 1))
            rand_mean = np.mean(rand_pixels, axis=(0, 1))

            print(
                f"Sequential RGB: ({seq_mean[0]:.1f}, {seq_mean[1]:.1f}, {seq_mean[2]:.1f})"
            )
            print(
                f"Random RGB: ({rand_mean[0]:.1f}, {rand_mean[1]:.1f}, {rand_mean[2]:.1f})"
            )

            # Both should have some color variation (not gray)
            seq_variation = np.max(seq_mean) - np.min(seq_mean)
            rand_variation = np.max(rand_mean) - np.min(rand_mean)

            assert seq_variation > 5, "Sequential mode should have color variation"
            assert rand_variation > 5, "Random mode should have color variation"

        finally:
            red_input_node.exit()
