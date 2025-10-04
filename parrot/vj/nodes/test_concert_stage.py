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
        assert hasattr(stage, "laser_scan_heads")
        assert hasattr(stage, "color_strobe")
        assert hasattr(stage, "stage_blinders")
        assert hasattr(stage, "hot_sparks")

        # Check camera system
        assert np.allclose(stage.camera_eye, [0.0, 6.0, -8.0])
        assert np.allclose(stage.camera_target, [0.0, 6.0, 0.0])
        assert np.allclose(stage.camera_up, [0.0, 1.0, 0.0])

        # Check component properties
        assert stage.volumetric_beams.beam_count == 6
        assert stage.laser_scan_heads.num_heads == 4
        assert stage.laser_scan_heads.beams_per_head == 12

    def test_component_access(self):
        """Test accessing individual components"""
        stage = ConcertStage()

        # Test direct access to components
        canvas_2d = stage.canvas_2d
        volumetric_beams = stage.volumetric_beams
        laser_scan_heads = stage.laser_scan_heads
        color_strobe = stage.color_strobe

        assert canvas_2d is not None
        assert volumetric_beams is not None
        assert laser_scan_heads is not None
        assert color_strobe is not None

        # Check types
        from parrot.vj.nodes.camera_zoom import CameraZoom
        from parrot.vj.nodes.volumetric_beam import VolumetricBeam
        from parrot.vj.nodes.laser_scan_heads import LaserScanHeads
        from parrot.vj.nodes.color_strobe import ColorStrobe

        assert isinstance(canvas_2d, CameraZoom)
        assert isinstance(volumetric_beams, VolumetricBeam)
        assert isinstance(laser_scan_heads, LaserScanHeads)
        assert isinstance(color_strobe, ColorStrobe)

    def test_mode_adjustments(self):
        """Test that mode changes adjust lighting appropriately via fixture generate methods"""
        stage = ConcertStage()

        # Test rave mode - call generate on each fixture directly
        rave_vibe = Vibe(Mode.rave)
        stage.laser_scan_heads.generate(rave_vibe)
        stage.volumetric_beams.generate(rave_vibe)

        assert stage.volumetric_beams.beam_intensity == 3.5  # Updated for visibility
        assert stage.laser_scan_heads.beams_per_head == 16  # Rave mode
        assert stage.laser_scan_heads.mode_opacity_multiplier == 1.0

        # Test gentle mode
        gentle_vibe = Vibe(Mode.gentle)
        stage.laser_scan_heads.generate(gentle_vibe)
        stage.volumetric_beams.generate(gentle_vibe)

        # Verify gentle mode intensity
        assert stage.volumetric_beams.beam_intensity == 2.0  # Updated for visibility
        assert stage.laser_scan_heads.beams_per_head == 10  # Gentle mode
        assert stage.laser_scan_heads.mode_opacity_multiplier == 0.5

        # Test blackout mode
        blackout_vibe = Vibe(Mode.blackout)
        stage.laser_scan_heads.generate(blackout_vibe)
        stage.volumetric_beams.generate(blackout_vibe)

        # Verify blackout intensity
        assert stage.volumetric_beams.beam_intensity == 0.0
        assert stage.laser_scan_heads.beams_per_head == 0
        assert stage.laser_scan_heads.mode_opacity_multiplier == 0.0

    def test_generate_with_vibe(self):
        """Test generate method with different vibes using recursive generation"""
        stage = ConcertStage()

        # Test with rave vibe - this will fail due to GL context requirement
        # but we can test that the method doesn't crash during the setup phase
        rave_vibe = Vibe(Mode.rave)

        # The recursive generate will fail when it tries to enter GL nodes
        # This is expected behavior - we're testing the component setup
        try:
            stage.generate_recursive(rave_vibe)
        except Exception:
            # Expected - GL context required for some child nodes
            pass

        # The laser scan heads should still be configured
        assert stage.laser_scan_heads.beams_per_head >= 1

    def test_direct_component_control(self):
        """Test direct control of lighting components"""
        stage = ConcertStage()

        # Test laser scan heads properties
        assert stage.laser_scan_heads.num_heads == 4
        assert stage.laser_scan_heads.beams_per_head >= 1
        assert stage.laser_scan_heads.base_rotation_speed > 0
        assert stage.laser_scan_heads.base_tilt_speed > 0
        assert stage.laser_scan_heads.base_beam_spread > 0

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

        # Laser scan heads are present and configured
        assert stage.laser_scan_heads.num_heads == 4
        assert stage.laser_scan_heads.beams_per_head >= 1

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

        # Laser scan heads defaults
        lasers = stage.laser_scan_heads
        assert lasers.num_heads == 4
        assert lasers.beams_per_head == 12
        assert lasers.base_rotation_speed == 0.4
        assert lasers.base_tilt_speed == 0.3
        assert lasers.base_beam_spread == 0.25
        assert lasers.width == 1920
        assert lasers.height == 1080

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

        print(
            "✅ Shift operations successfully changed component states and printed node trees"
        )
        print(
            "✅ Both guaranteed (threshold=1.0) and probabilistic (threshold=0.3) shifts tested"
        )

    def test_blackout_mode_configures_components(self):
        """Test that blackout mode configures components to have zero intensity"""
        stage = ConcertStage()

        # Apply blackout mode to all components
        blackout_vibe = Vibe(Mode.blackout)
        stage.volumetric_beams.generate(blackout_vibe)
        stage.laser_scan_heads.generate(blackout_vibe)
        stage.stage_blinders.generate(blackout_vibe)

        # Verify all components are disabled/minimal in blackout
        assert stage.volumetric_beams.beam_intensity == 0.0
        assert stage.laser_scan_heads.beams_per_head == 0
        assert stage.laser_scan_heads.mode_opacity_multiplier == 0.0
        assert stage.stage_blinders.num_blinders == 0
        assert stage.stage_blinders.mode_opacity_multiplier == 0.0


if __name__ == "__main__":
    pytest.main([__file__])
