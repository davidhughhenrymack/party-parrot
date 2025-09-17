#!/usr/bin/env python3

import pytest
import numpy as np
import moderngl as mgl
from unittest.mock import Mock, MagicMock

from parrot.vj.nodes.laser_array import LaserArray, LaserBeam
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.utils.colour import Color
from parrot.graph.BaseInterpretationNode import Vibe
from parrot.director.mode import Mode


class TestLaserBeam:
    """Test the LaserBeam class"""

    def test_init(self):
        """Test laser beam initialization"""
        beam_id = 5
        fan_angle = np.pi / 4

        laser = LaserBeam(beam_id, fan_angle)

        assert laser.beam_id == beam_id
        assert laser.fan_angle == fan_angle
        assert laser.intensity == 1.0


class TestLaserArray:
    """Test the LaserArray class"""

    def test_init(self):
        """Test laser array initialization"""
        camera_eye = np.array([0.0, 6.0, -8.0])
        camera_target = np.array([0.0, 6.0, 0.0])
        camera_up = np.array([0.0, 1.0, 0.0])
        laser_position = np.array([-4.0, 8.0, 2.0])
        laser_point_vector = np.array([1.0, 0.0, 0.0])

        laser_array = LaserArray(
            camera_eye=camera_eye,
            camera_target=camera_target,
            camera_up=camera_up,
            laser_position=laser_position,
            laser_point_vector=laser_point_vector,
            laser_count=6,
            laser_length=40.0,
            laser_thickness=0.1,
            width=800,
            height=600,
        )

        assert laser_array.laser_count == 6
        assert laser_array.laser_length == 40.0
        assert laser_array.laser_thickness == 0.1
        assert laser_array.width == 800
        assert laser_array.height == 600
        assert np.allclose(laser_array.camera_eye, camera_eye)
        assert np.allclose(laser_array.laser_position, laser_position)
        assert np.allclose(laser_array.laser_point_vector, laser_point_vector)

    def test_setup_lasers(self):
        """Test laser setup creates correct number of lasers"""
        camera_eye = np.array([0.0, 6.0, -8.0])
        camera_target = np.array([0.0, 6.0, 0.0])
        camera_up = np.array([0.0, 1.0, 0.0])
        laser_position = np.array([-4.0, 8.0, 2.0])
        laser_point_vector = np.array([1.0, 0.0, 0.0])

        laser_array = LaserArray(
            camera_eye=camera_eye,
            camera_target=camera_target,
            camera_up=camera_up,
            laser_position=laser_position,
            laser_point_vector=laser_point_vector,
            laser_count=8,
        )

        assert len(laser_array.lasers) == 8

        # All lasers should have different fan angles
        fan_angles = [laser.fan_angle for laser in laser_array.lasers]
        # Should have a range of angles
        assert (
            len(set(fan_angles)) > 1 or len(fan_angles) == 1
        )  # Allow single laser case

    def test_generate_vibe_rave(self):
        """Test generate method with rave mode"""
        camera_eye = np.array([0.0, 6.0, -8.0])
        camera_target = np.array([0.0, 6.0, 0.0])
        camera_up = np.array([0.0, 1.0, 0.0])
        laser_position = np.array([-4.0, 8.0, 2.0])
        laser_point_vector = np.array([1.0, 0.0, 0.0])

        laser_array = LaserArray(
            camera_eye=camera_eye,
            camera_target=camera_target,
            camera_up=camera_up,
            laser_position=laser_position,
            laser_point_vector=laser_point_vector,
            laser_count=4,
        )

        vibe = Vibe(mode=Mode.rave)
        laser_array.generate(vibe)

        # Should have picked a random signal
        assert isinstance(laser_array.fan_signal, FrameSignal)

    def test_generate_vibe_gentle(self):
        """Test generate method with gentle mode"""
        camera_eye = np.array([0.0, 6.0, -8.0])
        camera_target = np.array([0.0, 6.0, 0.0])
        camera_up = np.array([0.0, 1.0, 0.0])
        laser_position = np.array([-4.0, 8.0, 2.0])
        laser_point_vector = np.array([1.0, 0.0, 0.0])

        laser_array = LaserArray(
            camera_eye=camera_eye,
            camera_target=camera_target,
            camera_up=camera_up,
            laser_position=laser_position,
            laser_point_vector=laser_point_vector,
            laser_count=4,
        )

        vibe = Vibe(mode=Mode.gentle)
        laser_array.generate(vibe)

        # Should have picked a random signal
        assert isinstance(laser_array.fan_signal, FrameSignal)

    def test_laser_direction_calculation(self):
        """Test laser direction calculation"""
        camera_eye = np.array([0.0, 6.0, -8.0])
        camera_target = np.array([0.0, 6.0, 0.0])
        camera_up = np.array([0.0, 1.0, 0.0])
        laser_position = np.array([-4.0, 8.0, 2.0])
        laser_point_vector = np.array([1.0, 0.0, 0.0])

        laser_array = LaserArray(
            camera_eye=camera_eye,
            camera_target=camera_target,
            camera_up=camera_up,
            laser_position=laser_position,
            laser_point_vector=laser_point_vector,
            laser_count=3,
        )

        beam = laser_array.lasers[0]
        signal_value = 0.5

        direction = laser_array._get_laser_direction(beam, signal_value)

        # Direction should be normalized
        assert abs(np.linalg.norm(direction) - 1.0) < 1e-6
        assert isinstance(direction, np.ndarray)
        assert direction.shape == (3,)


class TestLaserArrayHeadlessRendering:
    """Test laser array with headless OpenGL rendering"""

    @pytest.fixture
    def headless_context(self):
        """Create a headless OpenGL context for testing"""
        try:
            # Create headless context
            context = mgl.create_context(standalone=True, require=330)
            return context
        except Exception as e:
            pytest.skip(f"Could not create headless OpenGL context: {e}")

    @pytest.fixture
    def mock_frame(self):
        """Create a mock frame with signal values"""
        frame = Mock(spec=Frame)
        frame.__getitem__ = Mock(
            side_effect=lambda signal: {
                FrameSignal.sustained_high: 0.7,
                FrameSignal.freq_high: 0.5,
                FrameSignal.freq_low: 0.3,
            }.get(signal, 0.0)
        )
        return frame

    @pytest.fixture
    def mock_color_scheme(self):
        """Create a mock color scheme"""
        scheme = Mock(spec=ColorScheme)
        fg_color = Mock(spec=Color)
        fg_color.rgb = (1.0, 0.0, 0.5)  # Pink color
        scheme.fg = fg_color
        return scheme

    @pytest.fixture
    def laser_array(self):
        """Create a laser array for testing"""
        camera_eye = np.array([0.0, 6.0, -8.0])
        camera_target = np.array([0.0, 6.0, 0.0])
        camera_up = np.array([0.0, 1.0, 0.0])
        laser_position = np.array([-4.0, 8.0, 2.0])
        laser_point_vector = np.array([1.0, 0.0, 0.0])

        return LaserArray(
            camera_eye=camera_eye,
            camera_target=camera_target,
            camera_up=camera_up,
            laser_position=laser_position,
            laser_point_vector=laser_point_vector,
            laser_count=4,
            laser_length=25.0,
            laser_thickness=0.05,
            width=512,
            height=512,
        )

    def test_headless_render_basic(
        self, headless_context, mock_frame, mock_color_scheme, laser_array
    ):
        """Test basic headless rendering without bloom"""
        # Initialize with headless context
        laser_array.enter(headless_context)

        try:
            # Test that resources were created
            assert laser_array._context is not None
            assert len(laser_array.lasers) == 4
            assert laser_array.framebuffer is not None
            assert laser_array.color_texture is not None
            assert laser_array.laser_program is not None
            assert laser_array.laser_vao is not None

            # Test render (should not crash)
            result = laser_array.render(mock_frame, mock_color_scheme, headless_context)

            # Should return a framebuffer
            assert result is not None
            assert hasattr(result, "use")  # Should be a framebuffer-like object

        finally:
            # Clean up
            laser_array.exit()

    def test_headless_render_with_bloom(
        self, headless_context, mock_frame, mock_color_scheme
    ):
        """Test headless rendering with bloom effect"""
        camera_eye = np.array([0.0, 6.0, -8.0])
        camera_target = np.array([0.0, 6.0, 0.0])
        camera_up = np.array([0.0, 1.0, 0.0])
        laser_position = np.array([-4.0, 8.0, 2.0])
        laser_point_vector = np.array([1.0, 0.0, 0.0])

        laser_array = LaserArray(
            camera_eye=camera_eye,
            camera_target=camera_target,
            camera_up=camera_up,
            laser_position=laser_position,
            laser_point_vector=laser_point_vector,
            laser_count=6,
            laser_length=30.0,
            laser_thickness=0.08,
            width=256,
            height=256,
        )

        # Initialize with headless context
        laser_array.enter(headless_context)

        try:
            # Test that bloom resources were created
            assert laser_array.bloom_framebuffer is not None
            assert laser_array.bloom_texture is not None
            assert laser_array.blur_framebuffer1 is not None
            assert laser_array.blur_framebuffer2 is not None
            assert laser_array.blur_program is not None
            assert laser_array.composite_program is not None
            assert laser_array.quad_vao is not None

            # Test render with bloom (should not crash)
            result = laser_array.render(mock_frame, mock_color_scheme, headless_context)

            # Should return the bloom framebuffer
            assert result is not None
            assert result == laser_array.bloom_framebuffer

        finally:
            # Clean up
            laser_array.exit()

    def test_headless_render_different_signals(
        self, headless_context, mock_color_scheme, laser_array
    ):
        """Test rendering with different signal values"""
        laser_array.enter(headless_context)

        try:
            # Test with high signal
            high_frame = Mock(spec=Frame)
            high_frame.__getitem__ = Mock(
                side_effect=lambda signal: {
                    FrameSignal.sustained_high: 1.0,
                    FrameSignal.freq_high: 1.0,
                }.get(signal, 0.0)
            )

            result_high = laser_array.render(
                high_frame, mock_color_scheme, headless_context
            )
            assert result_high is not None

            # Test with low signal
            low_frame = Mock(spec=Frame)
            low_frame.__getitem__ = Mock(
                side_effect=lambda signal: {
                    FrameSignal.sustained_high: 0.1,
                    FrameSignal.freq_high: 0.1,
                }.get(signal, 0.0)
            )

            result_low = laser_array.render(
                low_frame, mock_color_scheme, headless_context
            )
            assert result_low is not None

        finally:
            laser_array.exit()

    def test_headless_render_color_scheme_integration(
        self, headless_context, mock_frame, laser_array
    ):
        """Test that color scheme colors are properly used"""
        laser_array.enter(headless_context)

        try:
            # Test with different color schemes
            red_scheme = Mock(spec=ColorScheme)
            red_color = Mock(spec=Color)
            red_color.rgb = (1.0, 0.0, 0.0)
            red_scheme.fg = red_color

            blue_scheme = Mock(spec=ColorScheme)
            blue_color = Mock(spec=Color)
            blue_color.rgb = (0.0, 0.0, 1.0)
            blue_scheme.fg = blue_color

            # Both should render without error
            result_red = laser_array.render(mock_frame, red_scheme, headless_context)
            result_blue = laser_array.render(mock_frame, blue_scheme, headless_context)

            assert result_red is not None
            assert result_blue is not None

        finally:
            laser_array.exit()

    def test_resource_cleanup(self, headless_context, laser_array):
        """Test that resources are properly cleaned up"""
        # Initialize
        laser_array.enter(headless_context)

        # Verify resources exist
        assert laser_array._context is not None
        assert laser_array.framebuffer is not None

        # Clean up
        laser_array.exit()

        # Verify cleanup
        assert laser_array._context is None


if __name__ == "__main__":
    # Run the tests
    pytest.main([__file__, "-v"])
