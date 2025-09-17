#!/usr/bin/env python3

import pytest
import moderngl as mgl
import numpy as np
from unittest.mock import Mock

from parrot.vj.nodes.layer_compose import LayerCompose, LayerSpec, BlendMode
from parrot.vj.nodes.static_color import StaticColor
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.graph.BaseInterpretationNode import Vibe
from parrot.director.mode import Mode


class TestLayerComposeOpacity:
    """Test LayerCompose opacity functionality with pixel-wise verification"""

    @pytest.fixture
    def gl_context(self):
        """Create OpenGL context for testing"""
        try:
            return mgl.create_context(standalone=True, require=330)
        except Exception as e:
            pytest.skip(f"Cannot create OpenGL context for testing: {e}")

    @pytest.fixture
    def frame(self):
        """Create test frame"""
        return Frame({FrameSignal.freq_low: 0.5})

    @pytest.fixture
    def color_scheme(self):
        """Create test color scheme"""
        return Mock(spec=ColorScheme)

    def test_opacity_normal_blending_pixel_verification(self, gl_context, frame, color_scheme):
        """Test that opacity works correctly with normal blending using pixel verification"""
        # Create red and black layers (StaticColor expects 0.0-1.0 float values)
        red_layer = StaticColor(color=(1.0, 0.0, 0.0), width=64, height=64)  # Solid red
        black_layer = StaticColor(color=(0.0, 0.0, 0.0), width=64, height=64)  # Solid black
        
        # Test different opacity values
        test_cases = [
            (1.0, "Full opacity - should be pure red"),
            (0.5, "Half opacity - should be dark red"),
            (0.0, "Zero opacity - should be black"),
        ]
        
        for opacity, description in test_cases:
            print(f"\nTesting {description}")
            
            # Create layer composition: black base + red with opacity
            layer_compose = LayerCompose(
                LayerSpec(black_layer, BlendMode.NORMAL),  # Base layer: black
                LayerSpec(red_layer, BlendMode.NORMAL, opacity=opacity),  # Red with opacity
            )
            
            # Initialize and render
            layer_compose.enter(gl_context)
            try:
                result_framebuffer = layer_compose.render(frame, color_scheme, gl_context)
                
                if result_framebuffer:
                    # Read pixel data
                    result_framebuffer.use()
                    pixel_data = gl_context.read(
                        viewport=(0, 0, 64, 64),
                        components=4,  # RGBA
                        dtype=np.uint8
                    )
                    
                    # Convert to numpy array and get center pixel
                    pixels = np.frombuffer(pixel_data, dtype=np.uint8).reshape((64, 64, 4))
                    center_pixel = pixels[32, 32]  # Get center pixel (R, G, B, A)
                    
                    print(f"Center pixel RGBA: {center_pixel}")
                    
                    # Verify results based on expected opacity blending
                    if opacity == 1.0:
                        # Full opacity: should be pure red
                        assert center_pixel[0] > 200, f"Red channel should be high, got {center_pixel[0]}"
                        assert center_pixel[1] < 50, f"Green channel should be low, got {center_pixel[1]}"
                        assert center_pixel[2] < 50, f"Blue channel should be low, got {center_pixel[2]}"
                    elif opacity == 0.5:
                        # Half opacity: should be dark red (red mixed with black)
                        # Expected: red * 0.5 + black * (1-0.5) = red * 0.5 = ~127
                        expected_red = int(255 * opacity)
                        tolerance = 30  # Allow some tolerance for blending
                        assert abs(center_pixel[0] - expected_red) < tolerance, \
                            f"Red channel should be ~{expected_red}, got {center_pixel[0]}"
                        assert center_pixel[1] < 50, f"Green channel should be low, got {center_pixel[1]}"
                        assert center_pixel[2] < 50, f"Blue channel should be low, got {center_pixel[2]}"
                    elif opacity == 0.0:
                        # Zero opacity: should be black
                        assert center_pixel[0] < 50, f"Red channel should be low, got {center_pixel[0]}"
                        assert center_pixel[1] < 50, f"Green channel should be low, got {center_pixel[1]}"
                        assert center_pixel[2] < 50, f"Blue channel should be low, got {center_pixel[2]}"
                        
            finally:
                layer_compose.exit()

    def test_opacity_additive_blending_pixel_verification(self, gl_context, frame, color_scheme):
        """Test that opacity works correctly with additive blending"""
        # Create red layer and black base (StaticColor expects 0.0-1.0 float values)
        red_layer = StaticColor(color=(0.5, 0.0, 0.0), width=64, height=64)  # Half-intensity red
        black_layer = StaticColor(color=(0.0, 0.0, 0.0), width=64, height=64)  # Solid black
        
        # Create layer composition: black base + red with additive blending and opacity
        layer_compose = LayerCompose(
            LayerSpec(black_layer, BlendMode.NORMAL),  # Base layer: black
            LayerSpec(red_layer, BlendMode.ADDITIVE, opacity=0.5),  # Red with 50% opacity, additive
        )
        
        # Initialize and render
        layer_compose.enter(gl_context)
        try:
            result_framebuffer = layer_compose.render(frame, color_scheme, gl_context)
            
            if result_framebuffer:
                # Read pixel data
                result_framebuffer.use()
                pixel_data = gl_context.read(
                    viewport=(0, 0, 64, 64),
                    components=4,  # RGBA
                    dtype=np.uint8
                )
                
                # Convert to numpy array and get center pixel
                pixels = np.frombuffer(pixel_data, dtype=np.uint8).reshape((64, 64, 4))
                center_pixel = pixels[32, 32]  # Get center pixel (R, G, B, A)
                
                print(f"Additive blend center pixel RGBA: {center_pixel}")
                
                # For additive blending with 50% opacity:
                # Expected: black + (red * 0.5) = 0 + (128 * 0.5) = 64
                expected_red = int(128 * 0.5)
                tolerance = 30
                assert abs(center_pixel[0] - expected_red) < tolerance, \
                    f"Red channel should be ~{expected_red}, got {center_pixel[0]}"
                assert center_pixel[1] < 50, f"Green channel should be low, got {center_pixel[1]}"
                assert center_pixel[2] < 50, f"Blue channel should be low, got {center_pixel[2]}"
                        
        finally:
            layer_compose.exit()

    def test_opacity_comparison_different_values(self, gl_context, frame, color_scheme):
        """Test that different opacity values produce visibly different results"""
        red_layer = StaticColor(color=(255, 0, 0), width=64, height=64)
        black_layer = StaticColor(color=(0, 0, 0), width=64, height=64)
        
        opacity_values = [0.2, 0.5, 0.8]
        results = []
        
        for opacity in opacity_values:
            layer_compose = LayerCompose(
                LayerSpec(black_layer, BlendMode.NORMAL),
                LayerSpec(red_layer, BlendMode.NORMAL, opacity=opacity),
            )
            
            layer_compose.enter(gl_context)
            try:
                result_framebuffer = layer_compose.render(frame, color_scheme, gl_context)
                
                if result_framebuffer:
                    result_framebuffer.use()
                    pixel_data = gl_context.read(
                        viewport=(0, 0, 64, 64),
                        components=4,
                        dtype=np.uint8
                    )
                    
                    pixels = np.frombuffer(pixel_data, dtype=np.uint8).reshape((64, 64, 4))
                    center_pixel = pixels[32, 32]
                    results.append((opacity, center_pixel[0]))  # Store opacity and red value
                    
            finally:
                layer_compose.exit()
        
        # Verify that higher opacity produces higher red values
        print(f"Opacity vs Red values: {results}")
        for i in range(len(results) - 1):
            current_opacity, current_red = results[i]
            next_opacity, next_red = results[i + 1]
            
            assert next_red > current_red, \
                f"Higher opacity ({next_opacity}) should produce higher red value than lower opacity ({current_opacity}). Got {next_red} vs {current_red}"
