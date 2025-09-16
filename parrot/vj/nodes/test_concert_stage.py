#!/usr/bin/env python3

import pytest
from unittest.mock import Mock
import moderngl as mgl

from parrot.vj.nodes.concert_stage import ConcertStage
from parrot.graph.BaseInterpretationNode import Vibe
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode


class TestConcertStage:
    """Test ConcertStage grouping node functionality"""

    def test_initialization(self):
        """Test ConcertStage initialization"""
        stage = ConcertStage()

        # Should have all components
        assert hasattr(stage, "canvas_2d")
        assert hasattr(stage, "volumetric_beams")
        assert hasattr(stage, "laser_array")

        # Check component properties
        assert stage.volumetric_beams.beam_count == 6
        assert stage.laser_array.laser_count == 8
        assert stage.volumetric_beams.color == (1.0, 0.8, 0.6)  # Warm
        assert stage.laser_array.color == (0.0, 1.0, 0.0)  # Green

    def test_component_access(self):
        """Test accessing individual components"""
        stage = ConcertStage()

        # Test direct access to components
        canvas_2d = stage.canvas_2d
        volumetric_beams = stage.volumetric_beams
        laser_array = stage.laser_array

        assert canvas_2d is not None
        assert volumetric_beams is not None
        assert laser_array is not None

        # Check types
        from parrot.vj.nodes.camera_zoom import CameraZoom
        from parrot.vj.nodes.volumetric_beam import VolumetricBeam
        from parrot.vj.nodes.laser_array import LaserArray

        assert isinstance(canvas_2d, CameraZoom)
        assert isinstance(volumetric_beams, VolumetricBeam)
        assert isinstance(laser_array, LaserArray)

    def test_mode_adjustments(self):
        """Test that mode changes adjust lighting appropriately via fixture generate methods"""
        stage = ConcertStage()

        # Test rave mode - call generate on each fixture directly
        rave_vibe = Vibe(Mode.rave)
        stage.laser_array.generate(rave_vibe)
        stage.volumetric_beams.generate(rave_vibe)
        assert stage.laser_array.strobe_frequency == 8.0
        assert stage.volumetric_beams.beam_intensity == 3.5  # Updated for visibility

        # Test gentle mode
        gentle_vibe = Vibe(Mode.gentle)
        stage.laser_array.generate(gentle_vibe)
        stage.volumetric_beams.generate(gentle_vibe)
        assert stage.laser_array.strobe_frequency == 0.0
        assert stage.volumetric_beams.beam_intensity == 2.0  # Updated for visibility

        # Test blackout mode
        blackout_vibe = Vibe(Mode.blackout)
        stage.laser_array.generate(blackout_vibe)
        stage.volumetric_beams.generate(blackout_vibe)
        assert stage.laser_array.strobe_frequency == 0.0
        assert stage.volumetric_beams.beam_intensity == 0.0

    def test_generate_with_vibe(self):
        """Test generate method with different vibes using recursive generation"""
        stage = ConcertStage()

        # Test with rave vibe - use generate_recursive to trigger children
        rave_vibe = Vibe(Mode.rave)
        stage.generate_recursive(rave_vibe)
        # Should have adjusted lighting for rave mode via children's generate methods
        assert stage.laser_array.strobe_frequency == 8.0

        # Test with gentle vibe
        gentle_vibe = Vibe(Mode.gentle)
        stage.generate_recursive(gentle_vibe)
        # Should have adjusted lighting for gentle mode via children's generate methods
        assert stage.laser_array.strobe_frequency == 0.0
        assert stage.volumetric_beams.beam_intensity == 2.0  # Updated for visibility

    def test_direct_component_control(self):
        """Test direct control of lighting components"""
        stage = ConcertStage()

        # Test direct laser controls
        stage.laser_array.set_strobe_frequency(12.0)
        assert stage.laser_array.strobe_frequency == 12.0

        stage.laser_array.fan_out_beams()
        # Should have called fan_out_beams (hard to test without mocking)

        stage.laser_array.narrow_beams()
        # Should have called narrow_beams (hard to test without mocking)

        stage.laser_array.color = (1.0, 0.0, 0.0)
        assert stage.laser_array.color == (1.0, 0.0, 0.0)

        # Test direct beam controls
        stage.volumetric_beams.beam_intensity = 2.0
        assert stage.volumetric_beams.beam_intensity == 2.0

        stage.volumetric_beams.haze_density = 0.5
        assert stage.volumetric_beams.haze_density == 0.5

    def test_render_without_gl_context(self):
        """Test that render handles missing GL context gracefully"""
        stage = ConcertStage()

        frame = Mock(spec=Frame)
        frame.__getitem__ = Mock(return_value=0.5)
        scheme = Mock(spec=ColorScheme)
        context = Mock(spec=mgl.Context)

        # Should not crash without GL setup
        result = stage.render(frame, scheme, context)
        # Should return None when not set up
        assert result is None

    def test_enter_exit_lifecycle(self):
        """Test enter/exit lifecycle management"""
        stage = ConcertStage()
        context = Mock(spec=mgl.Context)

        # Mock GL resources
        mock_texture = Mock()
        mock_framebuffer = Mock()
        context.texture.return_value = mock_texture
        context.framebuffer.return_value = mock_framebuffer

        # Test just this node's enter method (not recursive)
        stage.enter(context)

        # ConcertStage no longer has its own GL resources - they're in LayerCompose
        # The enter method should do nothing for ConcertStage itself
        assert not hasattr(stage, "final_texture")
        assert not hasattr(stage, "_context")

        # Test just this node's exit method (not recursive)
        stage.exit()

        # ConcertStage exit should do nothing - resources managed by LayerCompose
        # No assertions needed as there are no resources to clean up

    def test_signal_configuration(self):
        """Test that components use appropriate audio signals"""
        stage = ConcertStage()

        # Volumetric beams should react to bass
        assert stage.volumetric_beams.signal == FrameSignal.freq_low

        # Laser array should react to treble
        assert stage.laser_array.signal == FrameSignal.freq_high

    def test_default_configuration(self):
        """Test default configuration values"""
        stage = ConcertStage()

        # Volumetric beams defaults
        beams = stage.volumetric_beams
        assert beams.beam_count == 6
        assert beams.beam_length == 12.0
        assert beams.beam_width == 0.4
        assert beams.beam_intensity == 2.5  # Updated for visibility
        assert beams.haze_density == 0.9  # Updated for visibility
        assert beams.movement_speed == 1.8

        # Laser array defaults
        lasers = stage.laser_array
        assert lasers.laser_count == 8
        assert lasers.array_radius == 2.5
        assert lasers.laser_length == 20.0
        assert lasers.laser_width == 0.02
        assert lasers.scan_speed == 2.5
        assert lasers.strobe_frequency == 0.0
        assert lasers.laser_intensity == 2.0


if __name__ == "__main__":
    pytest.main([__file__])
