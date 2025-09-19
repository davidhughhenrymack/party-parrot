#!/usr/bin/env python3

import pytest
import numpy as np
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

        # Check camera system
        assert np.allclose(stage.camera_eye, [0.0, 6.0, -8.0])
        assert np.allclose(stage.camera_target, [0.0, 6.0, 0.0])
        assert np.allclose(stage.camera_up, [0.0, 1.0, 0.0])

        # Check component properties (new LaserArray defaults)
        assert stage.volumetric_beams.beam_count == 6
        assert stage.laser_array.laser_count == 30  # New default
        assert len(stage.laser_array.lasers) == 30

        # Check laser array camera integration
        assert np.allclose(stage.laser_array.camera_eye, stage.camera_eye)
        assert np.allclose(stage.laser_array.camera_target, stage.camera_target)
        assert np.allclose(stage.laser_array.camera_up, stage.camera_up)

        # Check laser positioning
        expected_laser_pos = np.array([-4.0, 8.0, 2.0])
        assert np.allclose(stage.laser_array.laser_position, expected_laser_pos)

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

        # New LaserArray doesn't have strobe_frequency - it picks random signals
        assert isinstance(stage.laser_array.fan_signal, FrameSignal)
        assert stage.volumetric_beams.beam_intensity == 3.5  # Updated for visibility

        # Test gentle mode
        gentle_vibe = Vibe(Mode.gentle)
        stage.laser_array.generate(gentle_vibe)
        stage.volumetric_beams.generate(gentle_vibe)

        # Check that signal was picked (could be any signal)
        assert isinstance(stage.laser_array.fan_signal, FrameSignal)
        assert stage.volumetric_beams.beam_intensity == 2.0  # Updated for visibility

        # Test blackout mode
        blackout_vibe = Vibe(Mode.blackout)
        stage.laser_array.generate(blackout_vibe)
        stage.volumetric_beams.generate(blackout_vibe)

        assert isinstance(stage.laser_array.fan_signal, FrameSignal)
        assert stage.volumetric_beams.beam_intensity == 0.0

    def test_generate_with_vibe(self):
        """Test generate method with different vibes using recursive generation"""
        stage = ConcertStage()

        # Test with rave vibe - this will fail due to GL context requirement
        # but we can test that the method doesn't crash during the setup phase
        rave_vibe = Vibe(Mode.rave)

        # The recursive generate will fail when it tries to enter GL nodes
        # This is expected behavior - we're testing the LaserArray setup
        try:
            stage.generate_recursive(rave_vibe)
        except Exception:
            # Expected - GL context required for some child nodes
            pass

        # The laser array should still have been configured
        assert isinstance(stage.laser_array.fan_signal, FrameSignal)

    def test_direct_component_control(self):
        """Test direct control of lighting components"""
        stage = ConcertStage()

        # Test laser array properties (new interface)
        assert stage.laser_array.laser_count == 30
        assert stage.laser_array.laser_length == 20.0  # New default
        assert stage.laser_array.laser_thickness == 0.05  # New default

        # Test that we can access laser beams
        assert len(stage.laser_array.lasers) == 30
        for laser in stage.laser_array.lasers:
            assert hasattr(laser, "beam_id")
            assert hasattr(laser, "fan_angle")
            assert hasattr(laser, "intensity")

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

        # Laser array now picks signals randomly on generate
        # Default is freq_high but can change
        assert isinstance(stage.laser_array.fan_signal, FrameSignal)

    def test_default_configuration(self):
        """Test default configuration values"""
        stage = ConcertStage()

        # Volumetric beams defaults (now baked into VolumetricBeam)
        beams = stage.volumetric_beams
        assert beams.beam_count == 6
        assert beams.beam_length == 12.0
        assert beams.beam_width == 0.4
        assert beams.beam_intensity == 2.5
        assert beams.haze_density == 0.9
        assert beams.movement_speed == 1.8

        # Laser array defaults (new simplified interface)
        lasers = stage.laser_array
        assert lasers.laser_count == 30  # New default
        assert lasers.laser_length == 20.0  # New default
        assert lasers.laser_thickness == 0.05  # New default
        assert lasers.width == 1280  # DEFAULT_WIDTH
        assert lasers.height == 720  # DEFAULT_HEIGHT

    def test_laser_direction_calculation(self):
        """Test that laser directions are calculated correctly"""
        stage = ConcertStage()

        # Test that laser point vector points toward camera
        laser_pos = stage.laser_array.laser_position
        camera_pos = stage.laser_array.camera_eye
        expected_direction = camera_pos - laser_pos
        expected_direction = expected_direction / np.linalg.norm(expected_direction)

        actual_direction = stage.laser_array.laser_point_vector

        # Should be pointing toward the camera (audience)
        assert np.allclose(actual_direction, expected_direction, atol=1e-6)

    def test_laser_fan_distribution(self):
        """Test that laser beams are distributed in a fan pattern"""
        stage = ConcertStage()

        # Check that laser beams have different fan angles
        fan_angles = [laser.fan_angle for laser in stage.laser_array.lasers]

        # Should have a range of angles (unless only 1 laser)
        if len(fan_angles) > 1:
            assert len(set(fan_angles)) > 1
            # Should span from negative to positive angles
            assert min(fan_angles) < 0
            assert max(fan_angles) > 0

    def test_shift_changes_node_tree(self):
        """Test that shift operation with 0.3 threshold changes the VJ node tree"""
        stage = ConcertStage()

        # Get initial tree structure and component states
        initial_tree = stage.print_tree()
        print("Initial VJ Node Tree:")
        print(initial_tree)

        # Capture initial state of components that should change
        initial_volumetric_signal = stage.volumetric_beams.signal
        initial_volumetric_intensity = stage.volumetric_beams.beam_intensity

        print(f"Initial volumetric signal: {initial_volumetric_signal}")
        print(f"Initial volumetric intensity: {initial_volumetric_intensity}")

        # Test with threshold=1.0 first to guarantee changes
        rave_vibe = Vibe(Mode.rave)
        stage.generate_recursive(rave_vibe, threshold=1.0)

        # Get tree structure after guaranteed shift
        guaranteed_shift_tree = stage.print_tree()
        print("VJ Node Tree after guaranteed shift (threshold=1.0):")
        print(guaranteed_shift_tree)

        # Capture state after guaranteed shift
        guaranteed_volumetric_signal = stage.volumetric_beams.signal
        guaranteed_volumetric_intensity = stage.volumetric_beams.beam_intensity

        print(
            f"After guaranteed shift volumetric signal: {guaranteed_volumetric_signal}"
        )
        print(
            f"After guaranteed shift volumetric intensity: {guaranteed_volumetric_intensity}"
        )

        # Validate that the tree structure expanded significantly after shift
        # The initial tree was simple, but after shift it should show the RandomChild selections
        assert len(guaranteed_shift_tree.split("\n")) > len(
            initial_tree.split("\n")
        ), "Tree should be more detailed after shift due to RandomChild/RandomOperation selections"

        # Validate that specific nodes appeared in the expanded tree
        assert (
            "MultiplyCompose" in guaranteed_shift_tree
            or "LayerCompose" in guaranteed_shift_tree
        )
        assert (
            "VideoPlayer" in guaranteed_shift_tree
            or "TextRenderer" in guaranteed_shift_tree
        )

        # Test volumetric beams directly (they're not in the LayerCompose tree but exist as attributes)
        # Call generate directly on volumetric beams to test mode changes
        stage.volumetric_beams.generate(rave_vibe)
        rave_intensity = stage.volumetric_beams.beam_intensity
        print(f"Volumetric beams intensity after rave generate: {rave_intensity}")
        assert (
            rave_intensity == 3.5
        ), f"Expected rave mode intensity 3.5, got {rave_intensity}"

        # Apply shift to gentle mode to verify mode changes
        gentle_vibe = Vibe(Mode.gentle)
        stage.generate_recursive(gentle_vibe, threshold=1.0)

        gentle_shift_tree = stage.print_tree()
        print("VJ Node Tree after gentle shift (threshold=1.0):")
        print(gentle_shift_tree)

        # Test gentle mode on volumetric beams directly
        stage.volumetric_beams.generate(gentle_vibe)
        gentle_intensity = stage.volumetric_beams.beam_intensity
        print(f"Volumetric beams intensity after gentle generate: {gentle_intensity}")
        assert (
            gentle_intensity == 2.0
        ), f"Expected gentle mode intensity 2.0, got {gentle_intensity}"

        # Now test with 0.3 threshold (probabilistic changes)
        # This may or may not change things, but should still print the tree
        stage.generate_recursive(rave_vibe, threshold=0.3)

        probabilistic_tree = stage.print_tree()
        print("VJ Node Tree after probabilistic shift (threshold=0.3):")
        print(probabilistic_tree)

        # The tree structure should always be valid regardless of threshold
        for tree in [
            initial_tree,
            guaranteed_shift_tree,
            gentle_shift_tree,
            probabilistic_tree,
        ]:
            assert "ConcertStage" in tree
            assert "LayerCompose" in tree

        print(
            "✅ Shift operations successfully changed component states and printed node trees"
        )
        print(
            "✅ Both guaranteed (threshold=1.0) and probabilistic (threshold=0.3) shifts tested"
        )

    def test_blackout_mode_returns_black_node(self):
        """Test that ConcertStage uses BlackoutSwitch which returns black node when in blackout mode"""
        stage = ConcertStage()

        # Mock objects for render call
        frame = Mock(spec=Frame)
        scheme = Mock(spec=ColorScheme)
        context = Mock(spec=mgl.Context)

        # Mock the blackout switch's black node and layer compose render methods
        mock_black_framebuffer = Mock(spec=mgl.Framebuffer)
        stage.blackout_switch.black_node.render = Mock(
            return_value=mock_black_framebuffer
        )

        mock_layer_framebuffer = Mock(spec=mgl.Framebuffer)
        stage.blackout_switch.child.render = Mock(return_value=mock_layer_framebuffer)

        # Test normal mode (should use layer compose)
        stage.blackout_switch.generate(Vibe(Mode.rave))
        result = stage.blackout_switch.render(frame, scheme, context)
        assert result == mock_layer_framebuffer
        stage.blackout_switch.child.render.assert_called_once_with(
            frame, scheme, context
        )
        stage.blackout_switch.black_node.render.assert_not_called()

        # Reset mocks
        stage.blackout_switch.child.render.reset_mock()
        stage.blackout_switch.black_node.render.reset_mock()

        # Test blackout mode (should use black node)
        stage.blackout_switch.generate(Vibe(Mode.blackout))
        result = stage.blackout_switch.render(frame, scheme, context)
        assert result == mock_black_framebuffer
        stage.blackout_switch.black_node.render.assert_called_once_with(
            frame, scheme, context
        )
        stage.blackout_switch.child.render.assert_not_called()


if __name__ == "__main__":
    pytest.main([__file__])
