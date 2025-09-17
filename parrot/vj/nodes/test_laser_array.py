#!/usr/bin/env python3

import pytest
import numpy as np
import moderngl as mgl
from unittest.mock import Mock, MagicMock

from parrot.vj.nodes.laser_array import LaserArray, LaserBeamState
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.utils.colour import Color
from parrot.graph.BaseInterpretationNode import Vibe
from parrot.director.mode import Mode


class TestLaserBeamState:
    """Test the LaserBeamState class"""

    def test_init(self):
        """Test laser beam state initialization"""
        position = np.array([1.0, 2.0, 3.0])
        direction = np.array([0.0, -1.0, 0.0])
        beam_id = 5

        laser = LaserBeamState(position, direction, beam_id)

        assert np.allclose(laser.position, position)
        assert np.allclose(laser.direction, direction)
        assert np.allclose(laser.target_position, position)
        assert np.allclose(laser.target_direction, direction)
        assert laser.beam_id == beam_id
        assert 0 <= laser.phase_offset <= 2 * np.pi
        assert 0 <= laser.scan_phase <= 2 * np.pi
        assert laser.intensity == 1.0
        assert laser.target_intensity == 1.0

    def test_update(self):
        """Test laser beam state update"""
        position = np.array([0.0, 10.0, 4.0])
        direction = np.array([0.0, -1.0, 0.0])
        laser = LaserBeamState(position, direction, 0)

        # Set different targets
        laser.target_position = np.array([1.0, 10.0, 4.0])
        laser.target_direction = np.array([0.1, -0.9, 0.0])
        laser.target_direction = laser.target_direction / np.linalg.norm(
            laser.target_direction
        )
        laser.target_intensity = 0.5

        # Update
        laser.update(time=1.0, speed=1.0, signal=0.5, fan_angle=np.pi / 4)

        # Position should move toward target
        assert not np.allclose(laser.position, position)
        # Direction should be normalized
        assert np.isclose(np.linalg.norm(laser.direction), 1.0)
        # Intensity should move toward target
        assert laser.intensity != 1.0

    def test_randomize_target(self):
        """Test target randomization"""
        position = np.array([0.0, 10.0, 4.0])
        direction = np.array([0.0, -1.0, 0.0])
        laser = LaserBeamState(position, direction, 0)

        array_center = np.array([0.0, 10.0, 4.0])
        spread_radius = 2.0

        original_target_pos = laser.target_position.copy()
        original_target_dir = laser.target_direction.copy()

        laser.randomize_target(array_center, spread_radius)

        # Target should have changed
        assert not np.allclose(laser.target_position, original_target_pos)
        assert not np.allclose(laser.target_direction, original_target_dir)
        # Direction should be normalized
        assert np.isclose(np.linalg.norm(laser.target_direction), 1.0)
        # Direction should point downward (negative Y)
        assert laser.target_direction[1] <= 0.0


class TestLaserArray:
    """Test the LaserArray class"""

    def test_init(self):
        """Test laser array initialization"""
        laser_array = LaserArray(
            laser_count=6,
            array_radius=3.0,
            laser_length=40.0,
            laser_width=0.1,
            fan_angle=np.pi / 2,
            scan_speed=2.0,
            strobe_frequency=5.0,
            laser_intensity=3.0,
            color=(1.0, 0.0, 0.0),
            signal=FrameSignal.freq_high,
            width=800,
            height=600,
        )

        assert laser_array.laser_count == 6
        assert laser_array.array_radius == 3.0
        assert laser_array.laser_length == 40.0
        assert laser_array.laser_width == 0.1
        assert laser_array.fan_angle == np.pi / 2
        assert laser_array.scan_speed == 2.0
        assert laser_array.strobe_frequency == 5.0
        assert laser_array.laser_intensity == 3.0
        assert laser_array.color == (1.0, 0.0, 0.0)
        assert laser_array.signal == FrameSignal.freq_high
        assert laser_array.width == 800
        assert laser_array.height == 600

    def test_setup_lasers(self):
        """Test laser setup creates correct number of lasers"""
        laser_array = LaserArray(laser_count=8)
        laser_array._setup_lasers()

        assert len(laser_array.lasers) == 8

        # All lasers should be positioned around the cluster center
        cluster_center = np.array([0.0, 10.0, 4.0])
        for laser in laser_array.lasers:
            # Should be within reasonable distance of cluster center
            distance = np.linalg.norm(laser.position - cluster_center)
            assert distance <= laser_array.array_radius + 1.0  # Allow some variation

            # Direction should be normalized and pointing downward
            assert np.isclose(np.linalg.norm(laser.direction), 1.0)
            assert laser.direction[1] <= 0.0

    def test_generate_vibe_rave(self):
        """Test generate method with rave mode"""
        laser_array = LaserArray(laser_count=4)
        laser_array._setup_lasers()

        vibe = Vibe(mode=Mode.rave)
        laser_array.generate(vibe)

        # Should have set strobe frequency
        assert laser_array.strobe_frequency > 0.0

    def test_generate_vibe_gentle(self):
        """Test generate method with gentle mode"""
        laser_array = LaserArray(laser_count=4)
        laser_array._setup_lasers()

        vibe = Vibe(mode=Mode.gentle)
        laser_array.generate(vibe)

        # Should have no strobe
        assert laser_array.strobe_frequency == 0.0

    def test_strobe_factor_calculation(self):
        """Test strobe factor calculation"""
        laser_array = LaserArray()

        # No strobe
        laser_array.strobe_frequency = 0.0
        assert laser_array._calculate_strobe_factor(1.0) == 1.0

        # With strobe
        laser_array.strobe_frequency = 2.0  # 2 Hz
        factor1 = laser_array._calculate_strobe_factor(0.0)
        factor2 = laser_array._calculate_strobe_factor(0.25)  # Quarter period
        factor3 = laser_array._calculate_strobe_factor(0.5)  # Half period

        # Should alternate between 0 and 1
        assert factor1 in [0.0, 1.0]
        assert factor2 in [0.0, 1.0]
        assert factor3 in [0.0, 1.0]

    def test_fan_angle_setting(self):
        """Test fan angle setting with bounds"""
        laser_array = LaserArray()

        # Normal value
        laser_array.set_fan_angle(np.pi / 4)
        assert laser_array.fan_angle == np.pi / 4

        # Clamp to bounds
        laser_array.set_fan_angle(-0.5)
        assert laser_array.fan_angle == 0.0

        laser_array.set_fan_angle(4.0)
        assert laser_array.fan_angle == np.pi

    def test_strobe_frequency_setting(self):
        """Test strobe frequency setting"""
        laser_array = LaserArray()

        # Normal value
        laser_array.set_strobe_frequency(5.0)
        assert laser_array.strobe_frequency == 5.0

        # Zero is allowed
        laser_array.set_strobe_frequency(0.0)
        assert laser_array.strobe_frequency == 0.0

        # Negative should raise error
        with pytest.raises(ValueError):
            laser_array.set_strobe_frequency(-1.0)

    def test_beam_control_methods(self):
        """Test narrow_beams and fan_out_beams methods"""
        laser_array = LaserArray(laser_count=4)
        laser_array._setup_lasers()

        # Test narrow beams
        laser_array.narrow_beams()
        screen_center = np.array([0.0, 6.0, 0.0])

        for laser in laser_array.lasers:
            # All beams should point toward screen center
            expected_dir = screen_center - laser.position
            expected_dir = expected_dir / np.linalg.norm(expected_dir)
            if expected_dir[1] > 0.0:
                expected_dir[1] = -abs(expected_dir[1])
                expected_dir = expected_dir / np.linalg.norm(expected_dir)

            # Should be close to expected direction
            dot_product = np.dot(laser.target_direction, expected_dir)
            assert dot_product > 0.9  # Should be very similar

        # Test fan out beams
        laser_array.fan_out_beams()

        # Directions should be more varied now
        directions = [laser.target_direction for laser in laser_array.lasers]
        # Check that not all directions are identical
        first_dir = directions[0]
        assert not all(np.allclose(d, first_dir, atol=0.1) for d in directions[1:])


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

    def test_headless_render_basic(
        self, headless_context, mock_frame, mock_color_scheme
    ):
        """Test basic headless rendering without bloom"""
        laser_array = LaserArray(
            laser_count=4,
            laser_length=25.0,
            laser_width=0.05,
            width=512,
            height=512,
        )

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
        laser_array = LaserArray(
            laser_count=6,
            laser_length=30.0,
            laser_width=0.08,
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
        self, headless_context, mock_color_scheme
    ):
        """Test rendering with different signal values"""
        laser_array = LaserArray(
            laser_count=4,
            signal=FrameSignal.freq_high,
            width=128,
            height=128,
        )

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
        self, headless_context, mock_frame
    ):
        """Test that color scheme colors are properly used"""
        laser_array = LaserArray(
            laser_count=2,
            width=64,
            height=64,
        )

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

    def test_headless_render_strobe_effect(
        self, headless_context, mock_frame, mock_color_scheme
    ):
        """Test rendering with strobe effect"""
        laser_array = LaserArray(
            laser_count=3,
            strobe_frequency=10.0,  # 10 Hz strobe
            width=64,
            height=64,
        )

        laser_array.enter(headless_context)

        try:
            # Render multiple times to test strobe timing
            for i in range(5):
                result = laser_array.render(
                    mock_frame, mock_color_scheme, headless_context
                )
                assert result is not None

        finally:
            laser_array.exit()

    def test_resource_cleanup(self, headless_context):
        """Test that resources are properly cleaned up"""
        laser_array = LaserArray(laser_count=2, width=32, height=32)

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
