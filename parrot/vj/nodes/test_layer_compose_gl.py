#!/usr/bin/env python3

import pytest
import numpy as np
import moderngl as mgl

from parrot.vj.nodes.layer_compose import LayerCompose
from parrot.vj.nodes.static_color import StaticColor, Red, Green, Blue, White
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode
from parrot.utils.colour import Color
from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe


class TestLayerComposeGL:
    """Test LayerCompose with real OpenGL rendering"""

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

    def test_layer_compose_single_layer(self, gl_context, color_scheme):
        """Test LayerCompose with a single layer (should return input directly)"""
        red_layer = Red(width=128, height=128)
        compose_node = LayerCompose(red_layer)
        
        red_layer.enter(gl_context)
        compose_node.enter(gl_context)
        
        try:
            frame = Frame({FrameSignal.freq_low: 0.0})
            
            result_framebuffer = compose_node.render(frame, color_scheme, gl_context)
            
            fb_data = result_framebuffer.read()
            pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                (result_framebuffer.height, result_framebuffer.width, 3)
            )
            
            # Should be red (255, 0, 0)
            assert np.all(pixels[:, :, 0] == 255), "Red channel should be 255"
            assert np.all(pixels[:, :, 1] == 0), "Green channel should be 0"
            assert np.all(pixels[:, :, 2] == 0), "Blue channel should be 0"
            
            # Check dimensions
            assert result_framebuffer.width == 128
            assert result_framebuffer.height == 128
            
        finally:
            compose_node.exit()
            red_layer.exit()

    def test_layer_compose_two_layers(self, gl_context, color_scheme):
        """Test LayerCompose with two layers"""
        red_layer = Red(width=64, height=64)
        green_layer = Green(width=64, height=64)
        compose_node = LayerCompose(red_layer, green_layer)
        
        red_layer.enter(gl_context)
        green_layer.enter(gl_context)
        compose_node.enter(gl_context)
        
        try:
            frame = Frame({FrameSignal.freq_low: 0.0})
            
            result_framebuffer = compose_node.render(frame, color_scheme, gl_context)
            
            fb_data = result_framebuffer.read()
            pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                (result_framebuffer.height, result_framebuffer.width, 3)
            )
            
            # Should be a blend of red and green
            # The exact result depends on the blending implementation
            red_channel = np.mean(pixels[:, :, 0])
            green_channel = np.mean(pixels[:, :, 1])
            blue_channel = np.mean(pixels[:, :, 2])
            
            # Should have some color output (compositing may vary)
            total_brightness = red_channel + green_channel + blue_channel
            assert total_brightness > 0, f"Should have some color output, got RGB: ({red_channel:.1f}, {green_channel:.1f}, {blue_channel:.1f})"
            
            print(f"Two layer blend - RGB: ({red_channel:.1f}, {green_channel:.1f}, {blue_channel:.1f})")
            
        finally:
            compose_node.exit()
            green_layer.exit()
            red_layer.exit()

    def test_layer_compose_multiple_layers(self, gl_context, color_scheme):
        """Test LayerCompose with multiple layers"""
        red_layer = Red(width=128, height=128)
        green_layer = Green(width=128, height=128)
        blue_layer = Blue(width=128, height=128)
        compose_node = LayerCompose(red_layer, green_layer, blue_layer)
        
        red_layer.enter(gl_context)
        green_layer.enter(gl_context)
        blue_layer.enter(gl_context)
        compose_node.enter(gl_context)
        
        try:
            frame = Frame({FrameSignal.freq_low: 0.0})
            
            result_framebuffer = compose_node.render(frame, color_scheme, gl_context)
            
            fb_data = result_framebuffer.read()
            pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                (result_framebuffer.height, result_framebuffer.width, 3)
            )
            
            # Should be a blend of all three colors
            red_channel = np.mean(pixels[:, :, 0])
            green_channel = np.mean(pixels[:, :, 1])
            blue_channel = np.mean(pixels[:, :, 2])
            
            # Should have some color output from multiple layers
            total_brightness = red_channel + green_channel + blue_channel
            assert total_brightness > 0, f"Should have some color output, got RGB: ({red_channel:.1f}, {green_channel:.1f}, {blue_channel:.1f})"
            
            print(f"Three layer blend - RGB: ({red_channel:.1f}, {green_channel:.1f}, {blue_channel:.1f})")
            
        finally:
            compose_node.exit()
            blue_layer.exit()
            green_layer.exit()
            red_layer.exit()

    def test_layer_compose_empty_layers(self, gl_context, color_scheme):
        """Test LayerCompose with no layers"""
        compose_node = LayerCompose()
        
        compose_node.enter(gl_context)
        
        try:
            frame = Frame({FrameSignal.freq_low: 0.0})
            
            result_framebuffer = compose_node.render(frame, color_scheme, gl_context)
            
            # Should return some framebuffer (likely black)
            assert result_framebuffer is not None
            
            fb_data = result_framebuffer.read()
            pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                (result_framebuffer.height, result_framebuffer.width, 3)
            )
            
            # Should be black or at least valid
            assert pixels.shape[2] == 3, "Should have RGB channels"
            
        finally:
            compose_node.exit()

    def test_layer_compose_different_sizes(self, gl_context, color_scheme):
        """Test LayerCompose with layers of different sizes"""
        # Base layer determines output size
        large_red = Red(width=256, height=256)
        small_green = Green(width=128, height=128)
        compose_node = LayerCompose(large_red, small_green)
        
        large_red.enter(gl_context)
        small_green.enter(gl_context)
        compose_node.enter(gl_context)
        
        try:
            frame = Frame({FrameSignal.freq_low: 0.0})
            
            result_framebuffer = compose_node.render(frame, color_scheme, gl_context)
            
            # Output should match the first (base) layer size
            assert result_framebuffer.width == 256
            assert result_framebuffer.height == 256
            
            fb_data = result_framebuffer.read()
            pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                (256, 256, 3)
            )
            
            # Should have some color output
            red_channel = np.mean(pixels[:, :, 0])
            green_channel = np.mean(pixels[:, :, 1])
            blue_channel = np.mean(pixels[:, :, 2])
            
            total_brightness = red_channel + green_channel + blue_channel
            assert total_brightness > 0, f"Should have some color output, got RGB: ({red_channel:.1f}, {green_channel:.1f}, {blue_channel:.1f})"
            
            print(f"Mixed size layers - RGB: ({red_channel:.1f}, {green_channel:.1f}, {np.mean(pixels[:, :, 2]):.1f})")
            
        finally:
            compose_node.exit()
            small_green.exit()
            large_red.exit()

    def test_layer_compose_size_adaptation(self, gl_context, color_scheme):
        """Test that LayerCompose adapts to the base layer size"""
        sizes = [(64, 64), (128, 256), (320, 240)]
        
        for width, height in sizes:
            base_layer = White(width=width, height=height)
            overlay_layer = Red(width=32, height=32)  # Different size overlay
            compose_node = LayerCompose(base_layer, overlay_layer)
            
            base_layer.enter(gl_context)
            overlay_layer.enter(gl_context)
            compose_node.enter(gl_context)
            
            try:
                frame = Frame({FrameSignal.freq_low: 0.0})
                
                result_framebuffer = compose_node.render(frame, color_scheme, gl_context)
                
                # Output should match base layer size
                assert result_framebuffer.width == width
                assert result_framebuffer.height == height
                
                fb_data = result_framebuffer.read()
                pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                    (height, width, 3)
                )
                
                # Should have some content
                assert np.any(pixels > 0), f"Size {width}x{height}: Should have non-black pixels"
                
            finally:
                compose_node.exit()
                overlay_layer.exit()
                base_layer.exit()

    def test_layer_compose_with_none_layers(self, gl_context, color_scheme):
        """Test LayerCompose handles layers that return None gracefully"""
        # Create a mock layer that returns None
        class NoneLayer(BaseInterpretationNode):
            def __init__(self):
                super().__init__([])
            def enter(self, context):
                pass
            def exit(self):
                pass
            def generate(self, vibe):
                pass
            def render(self, frame, scheme, context):
                return None
        
        red_layer = Red(width=128, height=128)
        none_layer = NoneLayer()
        compose_node = LayerCompose(red_layer, none_layer)
        
        red_layer.enter(gl_context)
        none_layer.enter(gl_context)
        compose_node.enter(gl_context)
        
        try:
            frame = Frame({FrameSignal.freq_low: 0.0})
            
            result_framebuffer = compose_node.render(frame, color_scheme, gl_context)
            
            # Should still work and return the red layer
            fb_data = result_framebuffer.read()
            pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape(
                (result_framebuffer.height, result_framebuffer.width, 3)
            )
            
            # Should be mostly red since the None layer is skipped
            red_channel = np.mean(pixels[:, :, 0])
            assert red_channel > 200, "Should be mostly red"
            
        finally:
            compose_node.exit()
            none_layer.exit()
            red_layer.exit()
