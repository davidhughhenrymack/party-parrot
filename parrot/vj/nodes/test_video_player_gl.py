#!/usr/bin/env python3

import pytest
import numpy as np
import moderngl as mgl
import os

from parrot.vj.nodes.video_player import VideoPlayer
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode
from parrot.utils.colour import Color
from parrot.graph.BaseInterpretationNode import Vibe


class TestVideoPlayerGL:
    """Test VideoPlayer with real OpenGL rendering"""

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
    def color_scheme(self):
        """Create a color scheme"""
        return ColorScheme(
            fg=Color("red"), bg=Color("black"), bg_contrast=Color("white")
        )

    def test_video_player_no_videos_fallback(self, gl_context, color_scheme):
        """Test VideoPlayer when no videos are available (should render black)"""
        # Use a non-existent video group
        video_node = VideoPlayer(fn_group="nonexistent", video_group="test")
        
        video_node.enter(gl_context)
        
        try:
            # Generate to try to load videos (will fail gracefully)
            vibe = Vibe(mode=Mode.rave)
            video_node.generate(vibe)
            
            frame = Frame({FrameSignal.freq_low: 0.0})
            
            result_framebuffer = video_node.render(frame, color_scheme, gl_context)
            
            # Should return a framebuffer (likely black or default size)
            assert result_framebuffer is not None
            
            # Should have reasonable dimensions
            assert result_framebuffer.width > 0
            assert result_framebuffer.height > 0
            
            fb_data = result_framebuffer.read()
            pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                (result_framebuffer.height, result_framebuffer.width, 3)
            )
            
            # Should be valid pixel data
            assert pixels.shape[2] == 3, "Should have RGB channels"
            
            print(f"No videos fallback - Dimensions: {result_framebuffer.width}x{result_framebuffer.height}")
            
        finally:
            video_node.exit()

    def test_video_player_initialization_sizes(self, gl_context, color_scheme):
        """Test VideoPlayer initialization and basic rendering without actual video files"""
        video_node = VideoPlayer(fn_group="bg", video_group="test_group")
        
        video_node.enter(gl_context)
        
        try:
            frame = Frame({FrameSignal.freq_low: 0.0})
            
            # Render without generating (no videos loaded)
            result_framebuffer = video_node.render(frame, color_scheme, gl_context)
            
            # Should return a valid framebuffer
            assert result_framebuffer is not None
            
            # Check that it has reasonable default dimensions
            assert result_framebuffer.width > 0
            assert result_framebuffer.height > 0
            
            fb_data = result_framebuffer.read()
            pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                (result_framebuffer.height, result_framebuffer.width, 3)
            )
            
            # Should be valid RGB data
            assert pixels.dtype == np.uint8
            assert pixels.shape[2] == 3
            
            print(f"Video player default - Dimensions: {result_framebuffer.width}x{result_framebuffer.height}")
            
        finally:
            video_node.exit()

    def test_video_player_generate_without_files(self, gl_context, color_scheme):
        """Test VideoPlayer generate method when no video files exist"""
        video_node = VideoPlayer(fn_group="bg", video_group="nonexistent_group")
        
        video_node.enter(gl_context)
        
        try:
            # Generate should handle missing video directories gracefully
            vibe = Vibe(mode=Mode.rave)
            video_node.generate(vibe)  # Should not crash
            
            # Should have handled the generate call without crashing
            # (May or may not find videos depending on test environment)
            assert isinstance(video_node.video_files, list)
            
            frame = Frame({FrameSignal.freq_low: 0.0})
            
            result_framebuffer = video_node.render(frame, color_scheme, gl_context)
            
            # Should still render something (fallback)
            assert result_framebuffer is not None
            
        finally:
            video_node.exit()

    def test_video_player_multiple_renders(self, gl_context, color_scheme):
        """Test VideoPlayer with multiple render calls"""
        video_node = VideoPlayer(fn_group="bg")
        
        video_node.enter(gl_context)
        
        try:
            frame = Frame({FrameSignal.freq_low: 0.0})
            
            # Render multiple times to test consistency
            framebuffers = []
            for i in range(3):
                result_framebuffer = video_node.render(frame, color_scheme, gl_context)
                framebuffers.append(result_framebuffer)
                
                assert result_framebuffer is not None
                assert result_framebuffer.width > 0
                assert result_framebuffer.height > 0
            
            # All framebuffers should have the same dimensions
            first_fb = framebuffers[0]
            for fb in framebuffers[1:]:
                assert fb.width == first_fb.width
                assert fb.height == first_fb.height
            
        finally:
            video_node.exit()

    def test_video_player_different_groups(self, gl_context, color_scheme):
        """Test VideoPlayer with different video groups"""
        groups_to_test = ["bg", "test_group", "another_group"]
        
        for group in groups_to_test:
            video_node = VideoPlayer(fn_group="bg", video_group=group)
            
            video_node.enter(gl_context)
            
            try:
                vibe = Vibe(mode=Mode.rave)
                video_node.generate(vibe)
                
                frame = Frame({FrameSignal.freq_low: 0.0})
                
                result_framebuffer = video_node.render(frame, color_scheme, gl_context)
                
                # Should handle any group gracefully
                assert result_framebuffer is not None
                
                print(f"Group '{group}': {len(video_node.video_files)} videos found")
                
            finally:
                video_node.exit()

    def test_video_player_fps_and_timing(self, gl_context, color_scheme):
        """Test VideoPlayer FPS and timing properties"""
        video_node = VideoPlayer(fn_group="bg")
        
        video_node.enter(gl_context)
        
        try:
            # Check default FPS
            assert video_node.fps > 0, "FPS should be positive"
            assert video_node.fps <= 120, "FPS should be reasonable"
            
            # Check timing properties
            assert hasattr(video_node, 'last_frame_time')
            assert video_node.last_frame_time >= 0
            
            frame = Frame({FrameSignal.freq_low: 0.0})
            
            result_framebuffer = video_node.render(frame, color_scheme, gl_context)
            
            # Should still work without actual video
            assert result_framebuffer is not None
            
        finally:
            video_node.exit()

    def test_video_player_resource_cleanup(self, gl_context, color_scheme):
        """Test VideoPlayer resource cleanup"""
        video_node = VideoPlayer(fn_group="bg")
        
        # Test enter/exit cycle
        video_node.enter(gl_context)
        
        frame = Frame({FrameSignal.freq_low: 0.0})
        result_framebuffer = video_node.render(frame, color_scheme, gl_context)
        
        # Should work normally
        assert result_framebuffer is not None
        
        # Exit should clean up resources
        video_node.exit()
        
        # Should be able to enter again
        video_node.enter(gl_context)
        
        try:
            result_framebuffer = video_node.render(frame, color_scheme, gl_context)
            assert result_framebuffer is not None
            
        finally:
            video_node.exit()

    def test_video_player_context_storage(self, gl_context, color_scheme):
        """Test VideoPlayer context storage and management"""
        video_node = VideoPlayer(fn_group="bg")
        
        # Before enter, context should be None
        assert video_node._context is None
        
        video_node.enter(gl_context)
        
        try:
            # After enter, context should be stored
            assert video_node._context is not None
            
            frame = Frame({FrameSignal.freq_low: 0.0})
            result_framebuffer = video_node.render(frame, color_scheme, gl_context)
            
            assert result_framebuffer is not None
            
        finally:
            video_node.exit()
            
        # After exit, context should be cleared
        assert video_node._context is None
