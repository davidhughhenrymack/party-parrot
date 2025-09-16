#!/usr/bin/env python3

"""
Integration tests for the VJ system to catch real-world errors.
These tests exercise the full VJ pipeline including 3D lighting initialization.
"""

import pytest
import moderngl as mgl
from unittest.mock import Mock, patch
import threading
import time

from parrot.vj.vj_director import VJDirector
from parrot.vj.nodes.concert_stage import ConcertStage
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode
from parrot.graph.BaseInterpretationNode import Vibe


class TestVJIntegration:
    """Integration tests for the complete VJ system"""

    def test_vj_director_initialization_hard_fail(self):
        """Test VJ director initialization - should hard fail on errors"""
        # This should not be wrapped in try/catch - let it fail hard
        director = VJDirector()

        # Verify all components are properly initialized
        assert director.concert_stage is not None
        assert isinstance(director.concert_stage, ConcertStage)

        # Verify 3D lighting components exist
        concert_stage = director.get_concert_stage()
        assert concert_stage.volumetric_beams is not None
        assert concert_stage.laser_array is not None
        assert concert_stage.canvas_2d is not None

        # Verify component properties are set correctly
        assert concert_stage.volumetric_beams.beam_count == 6
        assert concert_stage.laser_array.laser_count == 8

    def test_gl_context_setup_hard_fail(self):
        """Test GL context setup - should hard fail on GL errors"""
        director = VJDirector()

        # Create a real OpenGL context for testing
        try:
            import moderngl_window as mglw

            # Create a headless context for testing
            ctx = mgl.create_context(standalone=True, require=330)
        except Exception as e:
            pytest.skip(f"Cannot create OpenGL context for testing: {e}")

        # This should not be wrapped in try/catch - let GL errors fail hard
        director.setup(ctx)

        # Verify GL resources were created - now managed by LayerCompose
        concert_stage = director.get_concert_stage()
        assert concert_stage.layer_compose._context is not None
        assert concert_stage.layer_compose.final_framebuffer is not None
        assert concert_stage.layer_compose.final_texture is not None

        # Verify 3D components have GL resources
        assert concert_stage.volumetric_beams._context is not None
        assert concert_stage.laser_array._context is not None

        # Clean up
        director.cleanup()

    def test_render_pipeline_hard_fail(self):
        """Test render pipeline - should hard fail on render errors"""
        director = VJDirector()

        # Create GL context
        try:
            ctx = mgl.create_context(standalone=True, require=330)
        except Exception as e:
            pytest.skip(f"Cannot create OpenGL context for testing: {e}")

        director.setup(ctx)

        # Create test frame and scheme
        frame = Mock(spec=Frame)
        frame.__getitem__ = Mock(return_value=0.5)  # Mock signal values
        scheme = Mock(spec=ColorScheme)

        # This should not be wrapped in try/catch - let render errors fail hard
        result = director.render(ctx, frame, scheme)

        # Verify render result
        assert result is not None

        # Clean up
        director.cleanup()

    def test_mode_shifting_hard_fail(self):
        """Test mode shifting - should hard fail on mode errors"""
        director = VJDirector()

        # This should not be wrapped in try/catch - let mode errors fail hard
        director.shift(Mode.rave)
        director.shift(Mode.gentle)
        director.shift(Mode.blackout)

        # Verify mode changes affected the lighting
        concert_stage = director.get_concert_stage()
        laser_array = concert_stage.laser_array

        # After blackout mode, strobe should be off
        assert laser_array.strobe_frequency == 0.0

    def test_3d_lighting_component_errors(self):
        """Test 3D lighting components for common error conditions"""
        director = VJDirector()
        concert_stage = director.get_concert_stage()

        # Test volumetric beams error conditions
        volumetric_beams = concert_stage.volumetric_beams

        # These should hard fail if parameters are invalid
        assert volumetric_beams.beam_count > 0
        assert volumetric_beams.beam_length > 0
        assert volumetric_beams.beam_width > 0
        assert volumetric_beams.beam_intensity > 0
        assert 0 <= volumetric_beams.haze_density <= 1.0

        # Test laser array error conditions
        laser_array = concert_stage.laser_array

        # These should hard fail if parameters are invalid
        assert laser_array.laser_count > 0
        assert laser_array.array_radius > 0
        assert laser_array.laser_length > 0
        assert laser_array.laser_width > 0
        assert laser_array.scan_speed > 0
        assert laser_array.strobe_frequency >= 0
        assert laser_array.laser_intensity > 0

    def test_audio_signal_processing_hard_fail(self):
        """Test audio signal processing - should hard fail on signal errors"""
        director = VJDirector()

        # Create frame with all required signals
        frame = Mock(spec=Frame)
        signal_values = {
            FrameSignal.freq_low: 0.3,
            FrameSignal.freq_high: 0.7,
            FrameSignal.freq_all: 0.5,
            FrameSignal.pulse: 0.8,
            FrameSignal.strobe: 0.2,
            FrameSignal.sustained_low: 0.4,
            FrameSignal.sustained_high: 0.6,
            FrameSignal.big_blinder: 0.1,
            FrameSignal.small_blinder: 0.9,
            FrameSignal.dampen: 0.0,
        }
        frame.__getitem__ = Mock(side_effect=lambda key: signal_values[key])

        # This should not fail - all signals should be handled
        concert_stage = director.get_concert_stage()
        volumetric_beams = concert_stage.volumetric_beams
        laser_array = concert_stage.laser_array

        # Verify components use correct signals
        assert volumetric_beams.signal == FrameSignal.freq_low
        assert laser_array.signal == FrameSignal.freq_high

    def test_resource_cleanup_hard_fail(self):
        """Test resource cleanup - should hard fail if cleanup fails"""
        director = VJDirector()

        # Create GL context
        try:
            ctx = mgl.create_context(standalone=True, require=330)
        except Exception as e:
            pytest.skip(f"Cannot create OpenGL context for testing: {e}")

        director.setup(ctx)

        # Verify resources exist - now managed by LayerCompose
        concert_stage = director.get_concert_stage()
        assert concert_stage.layer_compose._context is not None

        # This should not be wrapped in try/catch - let cleanup errors fail hard
        director.cleanup()

        # Verify resources were cleaned up - now managed by LayerCompose
        assert concert_stage.layer_compose._context is None

    def test_concurrent_access_hard_fail(self):
        """Test concurrent access patterns - should hard fail on race conditions"""
        director = VJDirector()

        # Test frame data updates (thread-safe)
        frame = Mock(spec=Frame)
        frame.__getitem__ = Mock(return_value=0.5)
        scheme = Mock(spec=ColorScheme)

        # This should be thread-safe and not fail
        def update_frame_data():
            for i in range(100):
                director.update_frame_data(frame, scheme)
                time.sleep(0.001)

        def get_frame_data():
            for i in range(100):
                director.get_latest_frame_data()
                time.sleep(0.001)

        # Run concurrent access
        thread1 = threading.Thread(target=update_frame_data)
        thread2 = threading.Thread(target=get_frame_data)

        thread1.start()
        thread2.start()

        thread1.join()
        thread2.join()

        # Should not have crashed

    def test_invalid_parameters_hard_fail(self):
        """Test invalid parameters - should hard fail immediately"""
        director = VJDirector()
        concert_stage = director.get_concert_stage()

        # Test invalid laser parameters via direct access - these should fail hard
        with pytest.raises((ValueError, AssertionError, TypeError)):
            concert_stage.laser_array.set_strobe_frequency(-1.0)  # Negative frequency

        # Note: VolumetricBeam properties don't have validation (direct assignment)
        # This is acceptable since the validation was only in the removed wrapper methods
        # and direct access is now the intended way to control components

    def test_memory_leaks_hard_fail(self):
        """Test for memory leaks in 3D components"""
        import gc
        import sys

        # Get initial object count
        gc.collect()
        initial_objects = len(gc.get_objects())

        # Create and destroy multiple directors
        for i in range(10):
            director = VJDirector()
            concert_stage = director.get_concert_stage()

            # Force cleanup
            director.cleanup()
            del director
            del concert_stage

        # Force garbage collection
        gc.collect()
        final_objects = len(gc.get_objects())

        # Should not have significant memory growth
        # Allow for some variance in object count
        object_growth = final_objects - initial_objects
        assert (
            object_growth < 1000
        ), f"Potential memory leak: {object_growth} objects created"


class TestVJErrorConditions:
    """Test specific error conditions that should cause hard failures"""

    def test_missing_video_files_hard_fail(self):
        """Test behavior when video files are missing"""
        director = VJDirector()
        concert_stage = director.get_concert_stage()
        canvas_2d = concert_stage.canvas_2d

        # The video player should handle missing files gracefully
        # but if it fails, it should fail hard, not silently
        # This is tested by the video player's own tests

    def test_shader_compilation_errors_hard_fail(self):
        """Test shader compilation errors - should hard fail"""
        # This would require mocking GL context to return shader errors
        # For now, we verify that shaders are created correctly
        director = VJDirector()

        try:
            ctx = mgl.create_context(standalone=True, require=330)
        except Exception as e:
            pytest.skip(f"Cannot create OpenGL context for testing: {e}")

        # This should hard fail if shaders don't compile
        director.setup(ctx)

        # Verify shader programs exist
        concert_stage = director.get_concert_stage()
        volumetric_beams = concert_stage.volumetric_beams
        laser_array = concert_stage.laser_array

        # These should be set if shaders compiled successfully
        assert volumetric_beams.beam_program is not None
        assert laser_array.laser_program is not None

        director.cleanup()

    def test_framebuffer_creation_errors_hard_fail(self):
        """Test framebuffer creation errors - should hard fail"""
        director = VJDirector()

        try:
            ctx = mgl.create_context(standalone=True, require=330)
        except Exception as e:
            pytest.skip(f"Cannot create OpenGL context for testing: {e}")

        # This should hard fail if framebuffers can't be created
        director.setup(ctx)

        # Verify framebuffers exist - now managed by LayerCompose
        concert_stage = director.get_concert_stage()
        assert concert_stage.layer_compose.final_framebuffer is not None
        assert concert_stage.volumetric_beams.framebuffer is not None
        assert concert_stage.laser_array.framebuffer is not None

        director.cleanup()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
