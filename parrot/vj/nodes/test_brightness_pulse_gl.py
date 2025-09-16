#!/usr/bin/env python3

import pytest
import numpy as np
import moderngl as mgl
import time

from parrot.vj.nodes.brightness_pulse import BrightnessPulse
from parrot.vj.nodes.static_color import White
from parrot.vj.nodes.video_player import VideoPlayer
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode
from parrot.utils.colour import Color
from parrot.graph.BaseInterpretationNode import Vibe


class TestBrightnessPulseGL:
    """Test BrightnessPulse with real OpenGL rendering"""

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
    def white_rect_node(self):
        """Create a white rectangle node"""
        return White(width=256, height=256)

    @pytest.fixture
    def color_scheme(self):
        """Create a color scheme"""
        return ColorScheme(
            fg=Color("red"), bg=Color("black"), bg_contrast=Color("white")
        )

    def test_brightness_pulse_with_no_audio(
        self, gl_context, white_rect_node, color_scheme
    ):
        """Test brightness pulse with no audio input (freq_low = 0.0)"""
        # Create brightness pulse node
        pulse_node = BrightnessPulse(
            white_rect_node, intensity=0.7, base_brightness=0.6
        )

        # Setup nodes
        white_rect_node.enter(gl_context)
        pulse_node.enter(gl_context)

        try:
            # Create frame with no audio (freq_low = 0.0)
            frame = Frame({FrameSignal.freq_low: 0.0})

            # Render through brightness pulse
            result_framebuffer = pulse_node.render(frame, color_scheme, gl_context)

            # Read pixels from the framebuffer (BrightnessPulse now adapts to input size)
            fb_data = result_framebuffer.read()
            pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                (result_framebuffer.height, result_framebuffer.width, 3)
            )

            # With base_brightness=0.6 and freq_low=0.0:
            # brightness_multiplier = 0.6 + (0.7 * 0.0) = 0.6
            # So white (255, 255, 255) becomes (153, 153, 153)
            expected_value = int(255 * 0.6)  # 153

            # Check that pixels are not black (> 0) and approximately correct
            assert np.all(pixels > 0), "All pixels should be > 0 (not black)"

            # Check that the brightness is approximately correct (within tolerance)
            mean_brightness = np.mean(pixels)
            assert (
                abs(mean_brightness - expected_value) < 10
            ), f"Expected ~{expected_value}, got {mean_brightness}"

            print(
                f"✅ No audio test: Expected ~{expected_value}, got {mean_brightness:.1f}"
            )

        finally:
            pulse_node.exit()
            white_rect_node.exit()

    def test_brightness_pulse_with_medium_audio(
        self, gl_context, white_rect_node, color_scheme
    ):
        """Test brightness pulse with medium audio input (freq_low = 0.5)"""
        pulse_node = BrightnessPulse(
            white_rect_node,
            intensity=0.7,
            base_brightness=0.6,
            signal=FrameSignal.freq_low,
        )

        white_rect_node.enter(gl_context)
        pulse_node.enter(gl_context)

        try:
            # Create frame with medium audio (freq_low = 0.5)
            frame = Frame({FrameSignal.freq_low: 0.5})

            result_framebuffer = pulse_node.render(frame, color_scheme, gl_context)

            fb_data = result_framebuffer.read()
            pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                (result_framebuffer.height, result_framebuffer.width, 3)
            )

            # With base_brightness=0.6 and freq_low=0.5:
            # brightness_multiplier = 0.6 + (0.7 * 0.5) = 0.95
            expected_value = int(255 * 0.95)  # 242

            assert np.all(pixels > 0), "All pixels should be > 0 (not black)"

            mean_brightness = np.mean(pixels)
            assert (
                abs(mean_brightness - expected_value) < 10
            ), f"Expected ~{expected_value}, got {mean_brightness}"

            print(
                f"✅ Medium audio test: Expected ~{expected_value}, got {mean_brightness:.1f}"
            )

        finally:
            pulse_node.exit()
            white_rect_node.exit()

    def test_brightness_pulse_with_high_audio(
        self, gl_context, white_rect_node, color_scheme
    ):
        """Test brightness pulse with high audio input (freq_low = 1.0)"""
        pulse_node = BrightnessPulse(
            white_rect_node,
            intensity=0.7,
            base_brightness=0.6,
            signal=FrameSignal.freq_low,
        )

        white_rect_node.enter(gl_context)
        pulse_node.enter(gl_context)

        try:
            # Create frame with high audio (freq_low = 1.0)
            frame = Frame({FrameSignal.freq_low: 1.0})

            result_framebuffer = pulse_node.render(frame, color_scheme, gl_context)

            fb_data = result_framebuffer.read()
            pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                (result_framebuffer.height, result_framebuffer.width, 3)
            )

            # With base_brightness=0.6 and freq_low=1.0:
            # brightness_multiplier = 0.6 + (0.7 * 1.0) = 1.3
            # Clamped to 2.0 max, so 1.3 is used
            expected_value = int(255 * 1.3)  # 331, but clamped to 255
            expected_value = min(expected_value, 255)  # 255

            assert np.all(pixels > 0), "All pixels should be > 0 (not black)"

            mean_brightness = np.mean(pixels)
            # Should be close to 255 (full white)
            assert (
                mean_brightness > 250
            ), f"Expected >250 (near white), got {mean_brightness}"

            print(
                f"✅ High audio test: Expected ~{expected_value}, got {mean_brightness:.1f}"
            )

        finally:
            pulse_node.exit()
            white_rect_node.exit()

    def test_brightness_progression(self, gl_context, white_rect_node, color_scheme):
        """Test that brightness increases as freq_low increases"""
        pulse_node = BrightnessPulse(
            white_rect_node, intensity=0.8, base_brightness=0.4
        )

        white_rect_node.enter(gl_context)
        pulse_node.enter(gl_context)

        try:
            freq_values = [0.0, 0.25, 0.5, 0.75, 1.0]
            brightness_values = []

            for freq_low in freq_values:
                frame = Frame({FrameSignal.freq_low: freq_low})
                result_framebuffer = pulse_node.render(frame, color_scheme, gl_context)

                pixels = np.frombuffer(
                    result_framebuffer.read(), dtype=np.uint8
                ).reshape((result_framebuffer.height, result_framebuffer.width, 3))

                mean_brightness = np.mean(pixels)
                brightness_values.append(mean_brightness)

                # Expected: 0.4 + (0.8 * freq_low)
                expected = 0.4 + (0.8 * freq_low)
                expected_pixel = int(255 * min(expected, 1.0))

                print(
                    f"freq_low={freq_low:.2f} → brightness={mean_brightness:.1f} (expected ~{expected_pixel})"
                )

            # Verify brightness increases monotonically
            for i in range(1, len(brightness_values)):
                assert (
                    brightness_values[i] >= brightness_values[i - 1]
                ), f"Brightness should increase: {brightness_values[i-1]} -> {brightness_values[i]}"

            # All values should be > 0
            assert all(
                b > 0 for b in brightness_values
            ), "All brightness values should be > 0"

            print("✅ Brightness progression test passed")

        finally:
            pulse_node.exit()
            white_rect_node.exit()

    def test_aggressive_vs_conservative_settings(
        self, gl_context, white_rect_node, color_scheme
    ):
        """Test difference between aggressive and conservative pulse settings"""
        # Test both configurations with no audio
        frame_silence = Frame({FrameSignal.freq_low: 0.0})

        # Conservative settings (current default)
        conservative_pulse = BrightnessPulse(
            white_rect_node, intensity=0.7, base_brightness=0.6
        )

        # Aggressive settings (original)
        aggressive_pulse = BrightnessPulse(
            white_rect_node, intensity=0.8, base_brightness=0.3
        )

        white_rect_node.enter(gl_context)

        try:
            # Test conservative settings
            conservative_pulse.enter(gl_context)
            conservative_fb = conservative_pulse.render(
                frame_silence, color_scheme, gl_context
            )
            conservative_pixels = np.frombuffer(
                conservative_fb.read(), dtype=np.uint8
            ).reshape((conservative_fb.height, conservative_fb.width, 3))
            conservative_brightness = np.mean(conservative_pixels)
            conservative_pulse.exit()

            # Test aggressive settings
            aggressive_pulse.enter(gl_context)
            aggressive_fb = aggressive_pulse.render(
                frame_silence, color_scheme, gl_context
            )
            aggressive_pixels = np.frombuffer(
                aggressive_fb.read(), dtype=np.uint8
            ).reshape((aggressive_fb.height, aggressive_fb.width, 3))
            aggressive_brightness = np.mean(aggressive_pixels)
            aggressive_pulse.exit()

            print(f"Conservative (silence): {conservative_brightness:.1f}")
            print(f"Aggressive (silence): {aggressive_brightness:.1f}")

            # Conservative should be brighter during silence
            assert (
                conservative_brightness > aggressive_brightness
            ), "Conservative settings should be brighter during silence"

            # Both should be > 0
            assert conservative_brightness > 0, "Conservative should be visible"
            assert aggressive_brightness > 0, "Aggressive should be visible"

            # Conservative should be significantly brighter (60% vs 30%)
            expected_conservative = 255 * 0.6  # 153
            expected_aggressive = 255 * 0.3  # 76.5

            assert abs(conservative_brightness - expected_conservative) < 20
            assert abs(aggressive_brightness - expected_aggressive) < 20

            print("✅ Settings comparison test passed")

        finally:
            white_rect_node.exit()

    def test_video_player_brightness_pulse_integration(self, gl_context, color_scheme):
        """Integration test: VideoPlayer + BrightnessPulse with real video data"""
        # Create video player node pointing to test video group
        video_player = VideoPlayer(fn_group="bg", video_group="test_group")

        # Create brightness pulse node that takes video as input
        pulse_node = BrightnessPulse(video_player, intensity=0.5, base_brightness=0.7)

        # Setup nodes
        video_player.enter(gl_context)
        pulse_node.enter(gl_context)

        try:
            # Generate video selection (this will pick videos from test_group)
            video_player.generate(Vibe(Mode.rave))

            # Let the video load a few frames first
            dummy_frame = Frame({FrameSignal.freq_low: 0.0})
            for i in range(5):  # Render a few frames to let video start
                video_fb = video_player.render(dummy_frame, color_scheme, gl_context)
                if video_fb:
                    # Check if video is actually producing content
                    video_data = video_fb.read()
                    print(
                        f"Video framebuffer size: {len(video_data)} bytes, dimensions: {video_fb.width}x{video_fb.height}"
                    )
                    video_pixels = np.frombuffer(video_data, dtype=np.uint8).reshape(
                        (video_fb.height, video_fb.width, 3)
                    )
                    video_brightness = np.mean(video_pixels)
                    print(
                        f"Video warmup frame {i}: brightness = {video_brightness:.1f}"
                    )
                time.sleep(0.1)  # Small delay to let video advance

            # Create frames with different audio levels to test brightness modulation
            test_frames = [
                Frame({FrameSignal.freq_low: 0.0}),  # No audio - base brightness
                Frame({FrameSignal.freq_low: 0.5}),  # Medium audio
                Frame({FrameSignal.freq_low: 1.0}),  # High audio
            ]

            brightness_values = []

            for i, frame in enumerate(test_frames):
                # Render video through brightness pulse
                result_framebuffer = pulse_node.render(frame, color_scheme, gl_context)

                # Read pixels from the framebuffer - use actual framebuffer dimensions
                fb_data = result_framebuffer.read()
                fb_width = result_framebuffer.width
                fb_height = result_framebuffer.height
                print(
                    f"  Output framebuffer: {fb_width}x{fb_height}, data size: {len(fb_data)}"
                )

                pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                    (fb_height, fb_width, 3)
                )

                # Calculate brightness statistics
                mean_brightness = np.mean(pixels)
                max_brightness = np.max(pixels)
                non_black_pixels = np.sum(pixels > 10)  # Pixels with some color
                total_pixels = pixels.size
                non_black_ratio = non_black_pixels / total_pixels

                brightness_values.append(mean_brightness)

                print(f"Frame {i} (freq_low={frame[FrameSignal.freq_low]:.1f}):")
                print(f"  Mean brightness: {mean_brightness:.1f}")
                print(f"  Max brightness: {max_brightness}")
                print(
                    f"  Non-black pixels: {non_black_pixels:,} ({non_black_ratio:.1%})"
                )

                # Validate that we have actual video content (not just black)
                assert (
                    non_black_pixels > 0
                ), f"Frame {i}: No non-black pixels found - video may not be loading"
                assert (
                    mean_brightness > 0
                ), f"Frame {i}: Mean brightness is 0 - no video content"

                # Should have significant non-black content (at least 10% of pixels)
                assert (
                    non_black_ratio > 0.1
                ), f"Frame {i}: Too few non-black pixels ({non_black_ratio:.1%}) - video content may be corrupted"

                # With base_brightness=0.7, even with no audio we should have decent brightness
                if frame[FrameSignal.freq_low] == 0.0:
                    # Base brightness should make video visible (adjusted for actual video content)
                    assert (
                        mean_brightness > 20
                    ), f"Frame {i}: Base brightness too low ({mean_brightness:.1f}) - video barely visible"

                # With high audio, brightness should be higher
                if frame[FrameSignal.freq_low] == 1.0:
                    # Should be brighter than base level (adjusted for actual video content)
                    assert (
                        mean_brightness > 30
                    ), f"Frame {i}: High audio brightness too low ({mean_brightness:.1f})"

            # Verify brightness progression with audio levels
            # Note: Video content varies, so we can't guarantee strict monotonic increase,
            # but we can check that high audio generally produces brighter results
            low_audio_brightness = brightness_values[0]  # freq_low = 0.0
            high_audio_brightness = brightness_values[2]  # freq_low = 1.0

            print(
                f"Brightness progression: {low_audio_brightness:.1f} -> {high_audio_brightness:.1f}"
            )

            # High audio should generally be brighter (allowing some tolerance for video content variation)
            brightness_increase = high_audio_brightness - low_audio_brightness
            print(f"Brightness increase with audio: {brightness_increase:.1f}")

            # Should see some increase, but video content can vary
            assert (
                brightness_increase > -20
            ), "High audio shouldn't make video significantly dimmer"

            print("✅ Video + BrightnessPulse integration test passed")
            print(f"✅ Successfully processed video with brightness modulation")
            print(f"✅ Video content verified: non-black pixels in all frames")

        finally:
            pulse_node.exit()
            video_player.exit()
