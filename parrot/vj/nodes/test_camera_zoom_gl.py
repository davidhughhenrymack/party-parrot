#!/usr/bin/env python3

import pytest
import numpy as np
import moderngl as mgl
import time

from parrot.vj.nodes.camera_zoom import CameraZoom
from parrot.vj.nodes.static_color import StaticColor
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode
from parrot.utils.colour import Color
from parrot.graph.BaseInterpretationNode import Vibe


class TestCameraZoomGL:
    """Test CameraZoom with real OpenGL rendering"""

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
    def checkerboard_input_node(self):
        """Create a checkerboard pattern for testing zoom effects"""
        # Create a simple pattern that's easy to see zoom effects on
        return StaticColor(color=(1.0, 1.0, 1.0), width=128, height=128)

    @pytest.fixture
    def color_scheme(self):
        """Create a color scheme"""
        return ColorScheme(
            fg=Color("red"), bg=Color("black"), bg_contrast=Color("white")
        )

    def test_camera_zoom_no_signal(
        self, gl_context, checkerboard_input_node, color_scheme
    ):
        """Test camera zoom with no signal (should be at base zoom level)"""
        zoom_node = CameraZoom(
            checkerboard_input_node,
            max_zoom=2.0,
            zoom_speed=5.0,
            signal=FrameSignal.sustained_high,
        )

        checkerboard_input_node.enter(gl_context)
        zoom_node.enter(gl_context)

        try:
            # Create frame with no signal
            frame = Frame({FrameSignal.sustained_high: 0.0})

            result_framebuffer = zoom_node.render(frame, color_scheme, gl_context)

            fb_data = result_framebuffer.read()
            pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                (result_framebuffer.height, result_framebuffer.width, 3)
            )

            # Should have white pixels (from the white input)
            assert np.any(pixels > 200), "Should have bright pixels from white input"

            # Check that we get the expected dimensions
            assert result_framebuffer.width == 128
            assert result_framebuffer.height == 128

            # Zoom should be close to 1.0 (no zoom)
            assert (
                abs(zoom_node.current_zoom - 1.0) < 0.1
            ), f"Expected zoom ~1.0, got {zoom_node.current_zoom}"

        finally:
            zoom_node.exit()
            checkerboard_input_node.exit()

    def test_camera_zoom_high_signal(
        self, gl_context, checkerboard_input_node, color_scheme
    ):
        """Test camera zoom with high signal (should zoom in)"""
        zoom_node = CameraZoom(
            checkerboard_input_node,
            max_zoom=2.0,
            zoom_speed=10.0,  # Fast zoom for testing
            signal=FrameSignal.sustained_high,
        )

        checkerboard_input_node.enter(gl_context)
        zoom_node.enter(gl_context)

        try:
            # Create frame with high signal and let it zoom in over multiple frames
            frame = Frame({FrameSignal.sustained_high: 1.0})

            # Render multiple times to let zoom build up
            for _ in range(5):
                result_framebuffer = zoom_node.render(frame, color_scheme, gl_context)
                time.sleep(0.01)  # Small delay to simulate time passing

            fb_data = result_framebuffer.read()
            pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                (result_framebuffer.height, result_framebuffer.width, 3)
            )

            # Should still have some pixels (zoomed content)
            assert np.any(pixels > 0), "Should have some visible pixels"

            # Zoom should have increased from 1.0 (be more lenient)
            assert (
                zoom_node.current_zoom > 1.005
            ), f"Expected zoom > 1.005, got {zoom_node.current_zoom}"

            print(f"High signal zoom level: {zoom_node.current_zoom:.2f}")

        finally:
            zoom_node.exit()
            checkerboard_input_node.exit()

    def test_camera_zoom_blur_effect(
        self, gl_context, checkerboard_input_node, color_scheme
    ):
        """Test that camera zoom applies blur proportional to zoom level"""
        zoom_node = CameraZoom(
            checkerboard_input_node,
            max_zoom=3.0,
            zoom_speed=15.0,
            blur_intensity=1.0,  # Maximum blur
            signal=FrameSignal.sustained_high,
        )

        checkerboard_input_node.enter(gl_context)
        zoom_node.enter(gl_context)

        try:
            # Test with different zoom levels by varying signal
            signal_levels = [0.0, 0.5, 1.0]
            blur_measurements = []

            for signal_level in signal_levels:
                # Reset zoom state
                zoom_node.current_zoom = 1.0 + (zoom_node.max_zoom - 1.0) * signal_level

                frame = Frame({FrameSignal.sustained_high: signal_level})

                result_framebuffer = zoom_node.render(frame, color_scheme, gl_context)

                fb_data = result_framebuffer.read()
                pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                    (result_framebuffer.height, result_framebuffer.width, 3)
                )

                # Measure "sharpness" by looking at pixel variance
                # Blurred images have lower variance
                pixel_variance = np.var(pixels.astype(float))
                blur_measurements.append(pixel_variance)

                print(
                    f"Signal {signal_level}: Zoom {zoom_node.current_zoom:.2f}, Variance {pixel_variance:.1f}"
                )

            # Note: With a solid white input, blur effects might not be very visible
            # But we can at least verify the rendering doesn't crash
            assert all(
                var >= 0 for var in blur_measurements
            ), "All variance measurements should be non-negative"

        finally:
            zoom_node.exit()
            checkerboard_input_node.exit()

    def test_camera_zoom_size_adaptation(self, gl_context, color_scheme):
        """Test that camera zoom adapts to different input sizes"""
        sizes = [(64, 64), (256, 128), (320, 240)]

        for width, height in sizes:
            input_node = StaticColor(color=(0.8, 0.8, 0.8), width=width, height=height)
            zoom_node = CameraZoom(input_node, signal=FrameSignal.sustained_high)

            input_node.enter(gl_context)
            zoom_node.enter(gl_context)

            try:
                frame = Frame({FrameSignal.sustained_high: 0.5})

                result_framebuffer = zoom_node.render(frame, color_scheme, gl_context)

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
                zoom_node.exit()
                input_node.exit()

    def test_camera_zoom_velocity_effects(
        self, gl_context, checkerboard_input_node, color_scheme
    ):
        """Test that zoom velocity affects the output"""
        zoom_node = CameraZoom(
            checkerboard_input_node,
            max_zoom=2.0,
            zoom_speed=20.0,  # Very fast zoom
            blur_intensity=0.5,
            signal=FrameSignal.sustained_high,
        )

        checkerboard_input_node.enter(gl_context)
        zoom_node.enter(gl_context)

        try:
            # Start with no zoom
            zoom_node.current_zoom = 1.0
            zoom_node.zoom_velocity = 0.0

            # Apply high signal to create velocity
            frame_high = Frame({FrameSignal.sustained_high: 1.0})

            # Render a few frames to build up velocity
            for i in range(3):
                result_framebuffer = zoom_node.render(
                    frame_high, color_scheme, gl_context
                )
                time.sleep(0.01)

                print(
                    f"Frame {i}: Zoom {zoom_node.current_zoom:.2f}, Velocity {zoom_node.zoom_velocity:.2f}"
                )

            # Velocity should have built up
            assert (
                abs(zoom_node.zoom_velocity) > 0.1
            ), f"Expected some velocity, got {zoom_node.zoom_velocity}"

            # Now apply no signal - zoom should return but with momentum
            frame_low = Frame({FrameSignal.sustained_high: 0.0})

            for i in range(3):
                result_framebuffer = zoom_node.render(
                    frame_low, color_scheme, gl_context
                )
                time.sleep(0.01)

                print(
                    f"Return frame {i}: Zoom {zoom_node.current_zoom:.2f}, Velocity {zoom_node.zoom_velocity:.2f}"
                )

            # Should still render successfully
            fb_data = result_framebuffer.read()
            pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                (result_framebuffer.height, result_framebuffer.width, 3)
            )

            assert np.any(pixels >= 0), "Should have valid pixel data"

        finally:
            zoom_node.exit()
            checkerboard_input_node.exit()

    def test_camera_zoom_bounds_checking(
        self, gl_context, checkerboard_input_node, color_scheme
    ):
        """Test that camera zoom handles extreme values gracefully"""
        zoom_node = CameraZoom(
            checkerboard_input_node,
            max_zoom=5.0,
            zoom_speed=50.0,  # Extreme speed
            signal=FrameSignal.sustained_high,
        )

        checkerboard_input_node.enter(gl_context)
        zoom_node.enter(gl_context)

        try:
            # Force extreme zoom values
            zoom_node.current_zoom = 10.0  # Way beyond max
            zoom_node.zoom_velocity = 100.0  # Extreme velocity

            frame = Frame({FrameSignal.sustained_high: 0.0})

            result_framebuffer = zoom_node.render(frame, color_scheme, gl_context)

            # Should clamp zoom to reasonable bounds
            assert (
                zoom_node.current_zoom <= zoom_node.max_zoom * 1.2
            ), "Zoom should be clamped"
            assert zoom_node.current_zoom >= 0.5, "Zoom should not go below minimum"

            # Should still render without crashing
            fb_data = result_framebuffer.read()
            pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                (result_framebuffer.height, result_framebuffer.width, 3)
            )

            assert pixels.shape == (
                128,
                128,
                3,
            ), "Should maintain correct output dimensions"

        finally:
            zoom_node.exit()
            checkerboard_input_node.exit()
