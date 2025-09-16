#!/usr/bin/env python3

import pytest
import numpy as np
import moderngl as mgl

from parrot.vj.nodes.saturation_pulse import SaturationPulse
from parrot.vj.nodes.static_color import StaticColor
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode
from parrot.utils.colour import Color
from parrot.graph.BaseInterpretationNode import Vibe


class TestSaturationPulseGL:
    """Test SaturationPulse with real OpenGL rendering"""

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
        """Create a red input node for testing saturation effects"""
        return StaticColor(color=(1.0, 0.0, 0.0), width=128, height=128)

    @pytest.fixture
    def color_scheme(self):
        """Create a color scheme"""
        return ColorScheme(
            fg=Color("red"), bg=Color("black"), bg_contrast=Color("white")
        )

    def test_saturation_pulse_no_signal(self, gl_context, red_input_node, color_scheme):
        """Test saturation pulse with no audio signal (should use base saturation)"""
        saturation_node = SaturationPulse(
            red_input_node,
            intensity=0.8,
            base_saturation=0.2,
            signal=FrameSignal.freq_high,
        )

        red_input_node.enter(gl_context)
        saturation_node.enter(gl_context)

        try:
            # Create frame with no signal
            frame = Frame({FrameSignal.freq_high: 0.0})

            result_framebuffer = saturation_node.render(frame, color_scheme, gl_context)

            fb_data = result_framebuffer.read()
            pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                (result_framebuffer.height, result_framebuffer.width, 3)
            )

            # With base_saturation=0.2 and no signal, the red should be desaturated
            # Red (255, 0, 0) with 0.2 saturation should become more grayish
            red_channel = np.mean(pixels[:, :, 0])
            green_channel = np.mean(pixels[:, :, 1])
            blue_channel = np.mean(pixels[:, :, 2])

            # Red should still be the dominant channel but reduced
            assert red_channel > green_channel, "Red should still be dominant"
            assert red_channel > blue_channel, "Red should still be dominant"

            # But green and blue should be non-zero due to desaturation
            assert green_channel > 0, "Green should be non-zero due to desaturation"
            assert blue_channel > 0, "Blue should be non-zero due to desaturation"

            print(
                f"No signal - RGB: ({red_channel:.1f}, {green_channel:.1f}, {blue_channel:.1f})"
            )

        finally:
            saturation_node.exit()
            red_input_node.exit()

    def test_saturation_pulse_high_signal(
        self, gl_context, red_input_node, color_scheme
    ):
        """Test saturation pulse with high audio signal (should increase saturation)"""
        saturation_node = SaturationPulse(
            red_input_node,
            intensity=0.8,
            base_saturation=0.2,
            signal=FrameSignal.freq_high,
        )

        red_input_node.enter(gl_context)
        saturation_node.enter(gl_context)

        try:
            # Create frame with high signal
            frame = Frame({FrameSignal.freq_high: 1.0})

            result_framebuffer = saturation_node.render(frame, color_scheme, gl_context)

            fb_data = result_framebuffer.read()
            pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                (result_framebuffer.height, result_framebuffer.width, 3)
            )

            # With base_saturation=0.2 + intensity=0.8 * signal=1.0 = 1.0 saturation
            # Red should be more saturated (closer to pure red)
            red_channel = np.mean(pixels[:, :, 0])
            green_channel = np.mean(pixels[:, :, 1])
            blue_channel = np.mean(pixels[:, :, 2])

            # Red should be dominant and green/blue should be lower
            assert red_channel > 200, "Red should be highly saturated"
            assert (
                green_channel < red_channel * 0.3
            ), "Green should be much lower than red"
            assert (
                blue_channel < red_channel * 0.3
            ), "Blue should be much lower than red"

            print(
                f"High signal - RGB: ({red_channel:.1f}, {green_channel:.1f}, {blue_channel:.1f})"
            )

        finally:
            saturation_node.exit()
            red_input_node.exit()

    def test_saturation_pulse_progression(
        self, gl_context, red_input_node, color_scheme
    ):
        """Test saturation pulse with different signal levels"""
        saturation_node = SaturationPulse(
            red_input_node,
            intensity=0.6,
            base_saturation=0.1,
            signal=FrameSignal.freq_high,
        )

        red_input_node.enter(gl_context)
        saturation_node.enter(gl_context)

        try:
            signal_levels = [0.0, 0.3, 0.6, 1.0]
            red_values = []
            green_values = []

            for signal_level in signal_levels:
                frame = Frame({FrameSignal.freq_high: signal_level})

                result_framebuffer = saturation_node.render(
                    frame, color_scheme, gl_context
                )

                fb_data = result_framebuffer.read()
                pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                    (result_framebuffer.height, result_framebuffer.width, 3)
                )

                red_channel = np.mean(pixels[:, :, 0])
                green_channel = np.mean(pixels[:, :, 1])

                red_values.append(red_channel)
                green_values.append(green_channel)

                print(
                    f"Signal {signal_level}: RGB=({red_channel:.1f}, {green_channel:.1f}, {np.mean(pixels[:, :, 2]):.1f})"
                )

            # As signal increases, saturation should increase
            # Since red is already at max (255), we check that green decreases (less desaturation)
            # (more saturated = more pure red, less mixed colors)

            # Green should decrease as saturation increases (less gray mixed in)
            assert (
                green_values[-1] < green_values[0]
            ), "Green should decrease with higher saturation"

            # Red should stay high throughout
            assert all(r > 200 for r in red_values), "Red should remain high throughout"

        finally:
            saturation_node.exit()
            red_input_node.exit()

    def test_saturation_pulse_with_different_colors(self, gl_context, color_scheme):
        """Test saturation pulse with different input colors"""
        colors_to_test = [
            ((0.0, 1.0, 0.0), "green"),  # Pure green
            ((0.0, 0.0, 1.0), "blue"),  # Pure blue
            ((1.0, 1.0, 0.0), "yellow"),  # Yellow
            ((0.5, 0.5, 0.5), "gray"),  # Gray
        ]

        for color, color_name in colors_to_test:
            input_node = StaticColor(color=color, width=64, height=64)
            saturation_node = SaturationPulse(
                input_node,
                intensity=0.8,
                base_saturation=0.3,
                signal=FrameSignal.freq_high,
            )

            input_node.enter(gl_context)
            saturation_node.enter(gl_context)

            try:
                # Test with medium signal
                frame = Frame({FrameSignal.freq_high: 0.5})

                result_framebuffer = saturation_node.render(
                    frame, color_scheme, gl_context
                )

                fb_data = result_framebuffer.read()
                pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                    (result_framebuffer.height, result_framebuffer.width, 3)
                )

                # Just verify that we get some reasonable output
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

            finally:
                saturation_node.exit()
                input_node.exit()

    def test_saturation_pulse_size_adaptation(self, gl_context, color_scheme):
        """Test that saturation pulse adapts to different input sizes"""
        sizes = [(64, 64), (128, 256), (320, 240)]

        for width, height in sizes:
            red_input = StaticColor(color=(1.0, 0.0, 0.0), width=width, height=height)
            saturation_node = SaturationPulse(red_input, signal=FrameSignal.freq_high)

            red_input.enter(gl_context)
            saturation_node.enter(gl_context)

            try:
                frame = Frame({FrameSignal.freq_high: 0.5})

                result_framebuffer = saturation_node.render(
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
                saturation_node.exit()
                red_input.exit()
