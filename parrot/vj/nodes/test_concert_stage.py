#!/usr/bin/env python3

import pytest
import numpy as np
from unittest.mock import Mock
import moderngl as mgl

from parrot.vj.nodes.concert_stage import ConcertStage
from parrot.graph.BaseInterpretationNode import Vibe
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.vj.vj_mode import VJMode


class TestConcertStage:
    """Test ConcertStage grouping node functionality"""

    def test_initialization(self):
        """Test ConcertStage initialization"""
        stage = ConcertStage()

        # Should have all components (wrapped in ModeSwitch)
        assert hasattr(stage, "canvas_2d")
        assert hasattr(stage, "laser_scan_heads")
        assert hasattr(stage, "color_strobe")
        assert hasattr(stage, "stage_blinders")
        assert hasattr(stage, "hot_sparks")

        # Check camera system
        assert np.allclose(stage.camera_eye, [0.0, 6.0, -8.0])
        assert np.allclose(stage.camera_target, [0.0, 6.0, 0.0])
        assert np.allclose(stage.camera_up, [0.0, 1.0, 0.0])

    def test_component_access(self):
        """Test accessing individual components"""
        stage = ConcertStage()

        # Test direct access to components (now wrapped in ModeSwitch)
        canvas_2d = stage.canvas_2d
        laser_scan_heads = stage.laser_scan_heads
        color_strobe = stage.color_strobe
        stage_blinders = stage.stage_blinders
        hot_sparks = stage.hot_sparks

        assert canvas_2d is not None
        assert laser_scan_heads is not None
        assert color_strobe is not None
        assert stage_blinders is not None
        assert hot_sparks is not None

        # Check types - effects are wrapped in ModeSwitch
        from parrot.vj.nodes.camera_zoom import CameraZoom
        from parrot.vj.nodes.mode_switch import ModeSwitch

        assert isinstance(canvas_2d, CameraZoom)
        assert isinstance(laser_scan_heads, ModeSwitch)
        assert isinstance(color_strobe, ModeSwitch)
        assert isinstance(stage_blinders, ModeSwitch)
        assert isinstance(hot_sparks, ModeSwitch)

    def test_mode_adjustments(self):
        """Test that mode changes switch between different effect instances via ModeSwitch"""
        stage = ConcertStage()

        # Effects are now ModeSwitch instances that select different configurations
        # based on mode. We test that the ModeSwitch responds to generate calls.

        # Test full_rave mode
        rave_vibe = Vibe(VJMode.full_rave)
        stage.laser_scan_heads.generate(rave_vibe)

        # After generate, the current_child should be the rave instance
        from parrot.vj.nodes.laser_scan_heads import LaserScanHeads

        assert isinstance(stage.laser_scan_heads.current_child, LaserScanHeads)

        # Test early_rave mode
        gentle_vibe = Vibe(VJMode.early_rave)
        stage.laser_scan_heads.generate(gentle_vibe)

        # Current child should still be a LaserScanHeads but different instance
        assert isinstance(stage.laser_scan_heads.current_child, LaserScanHeads)

        # Test blackout mode - now uses Black() nodes
        blackout_vibe = Vibe(VJMode.blackout)
        stage.laser_scan_heads.generate(blackout_vibe)

        # Current child should be a Black node for blackout
        from parrot.vj.nodes.black import Black

        assert isinstance(stage.laser_scan_heads.current_child, Black)

    def test_generate_with_vibe(self):
        """Test generate method with different vibes using recursive generation"""
        stage = ConcertStage()

        # Test with full_rave vibe
        rave_vibe = Vibe(VJMode.full_rave)

        # The recursive generate will work for ModeSwitch nodes
        stage.generate_recursive(rave_vibe)

        # Verify ModeSwitch has selected appropriate children
        from parrot.vj.nodes.laser_scan_heads import LaserScanHeads

        assert isinstance(stage.laser_scan_heads.current_child, LaserScanHeads)

    def test_direct_component_control(self):
        """Test that ModeSwitch components can be accessed"""
        stage = ConcertStage()

        # Components are ModeSwitch instances
        from parrot.vj.nodes.mode_switch import ModeSwitch

        assert isinstance(stage.laser_scan_heads, ModeSwitch)
        assert isinstance(stage.stage_blinders, ModeSwitch)
        assert isinstance(stage.hot_sparks, ModeSwitch)

        # After initialization, ModeSwitch has a current_child
        assert stage.laser_scan_heads.current_child is not None

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
        """Test that ModeSwitch components are properly configured"""
        stage = ConcertStage()

        # Components are ModeSwitch instances with current children
        assert stage.laser_scan_heads.current_child is not None
        assert stage.color_strobe.current_child is not None
        assert stage.stage_blinders.current_child is not None

    def test_default_configuration(self):
        """Test default ModeSwitch configuration"""
        stage = ConcertStage()

        # All effect components are ModeSwitch instances
        from parrot.vj.nodes.mode_switch import ModeSwitch

        assert isinstance(stage.laser_scan_heads, ModeSwitch)
        assert isinstance(stage.color_strobe, ModeSwitch)
        assert isinstance(stage.stage_blinders, ModeSwitch)
        assert isinstance(stage.hot_sparks, ModeSwitch)

        # Each ModeSwitch starts with a current_child (defaults to first mode)
        assert stage.laser_scan_heads.current_child is not None
        assert stage.color_strobe.current_child is not None
        assert stage.stage_blinders.current_child is not None
        assert stage.hot_sparks.current_child is not None

    def test_shift_changes_node_tree(self):
        """Test that shift operation with 0.3 threshold changes the VJ node tree"""
        stage = ConcertStage()

        # Get initial tree structure
        initial_tree = stage.print_tree()
        print("Initial VJ Node Tree:")
        print(initial_tree)

        # Test with threshold=1.0 first to guarantee changes
        rave_vibe = Vibe(VJMode.full_rave)
        stage.generate_recursive(rave_vibe, threshold=1.0)

        # Get tree structure after guaranteed shift
        guaranteed_shift_tree = stage.print_tree()
        print("VJ Node Tree after guaranteed shift (threshold=1.0):")
        print(guaranteed_shift_tree)

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

        # Apply shift to early_rave mode to verify mode changes
        gentle_vibe = Vibe(VJMode.early_rave)
        stage.generate_recursive(gentle_vibe, threshold=1.0)

        gentle_shift_tree = stage.print_tree()
        print("VJ Node Tree after gentle shift (threshold=1.0):")
        print(gentle_shift_tree)

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
        """Test that blackout mode switches to Black() nodes"""
        stage = ConcertStage()

        # Apply blackout mode to all components
        blackout_vibe = Vibe(VJMode.blackout)
        stage.laser_scan_heads.generate(blackout_vibe)
        stage.stage_blinders.generate(blackout_vibe)
        stage.hot_sparks.generate(blackout_vibe)
        stage.color_strobe.generate(blackout_vibe)

        # Verify all ModeSwitch instances have switched to Black() nodes for blackout
        from parrot.vj.nodes.black import Black

        assert isinstance(stage.laser_scan_heads.current_child, Black)
        assert isinstance(stage.stage_blinders.current_child, Black)
        assert isinstance(stage.hot_sparks.current_child, Black)
        assert isinstance(stage.color_strobe.current_child, Black)


if __name__ == "__main__":
    pytest.main([__file__])
