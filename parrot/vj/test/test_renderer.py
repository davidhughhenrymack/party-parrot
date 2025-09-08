import pytest
import numpy as np
from parrot.vj.renderer import ModernGLRenderer
from parrot.vj.base import SolidLayer
from parrot.director.frame import Frame
from parrot.director.color_scheme import ColorScheme
from parrot.utils.colour import Color


class TestModernGLRenderer:
    """Test the ModernGL renderer functionality"""

    def test_renderer_creation(self):
        renderer = ModernGLRenderer(800, 600)

        assert renderer.width == 800
        assert renderer.height == 600
        assert len(renderer.layers) == 0
        assert renderer.get_size() == (800, 600)

    def test_renderer_headless_mode(self):
        """Test that renderer can be created in headless mode"""
        renderer = ModernGLRenderer(640, 480, headless=True)

        assert renderer.width == 640
        assert renderer.height == 480
        # Should work even without a display

    def test_renderer_with_solid_layer(self):
        """Test rendering with a solid layer"""
        renderer = ModernGLRenderer(100, 100)
        layer = SolidLayer("test", (255, 128, 64), 200, width=100, height=100)
        renderer.add_layer(layer)

        frame = Frame({})
        scheme = ColorScheme(Color("red"), Color("blue"), Color("green"))

        result = renderer.render_frame(frame, scheme)

        assert result is not None
        assert result.shape == (100, 100, 4)
        assert result.dtype == np.uint8

        # Should have the solid color (allowing for some GPU precision differences)
        pixel = result[50, 50]  # Check center pixel
        assert abs(pixel[0] - 255) <= 2  # Red
        assert abs(pixel[1] - 128) <= 2  # Green
        assert abs(pixel[2] - 64) <= 2  # Blue
        assert abs(pixel[3] - 200) <= 2  # Alpha

    def test_renderer_fallback_to_cpu(self):
        """Test that renderer falls back to CPU when ModernGL fails"""
        renderer = ModernGLRenderer(50, 50)

        # Force CPU fallback by setting _initialized to False
        renderer._initialized = False

        layer = SolidLayer("test", (128, 128, 128), 255, width=50, height=50)
        renderer.add_layer(layer)

        frame = Frame({})
        scheme = ColorScheme(Color("red"), Color("blue"), Color("green"))

        result = renderer.render_frame(frame, scheme)

        assert result is not None
        assert result.shape == (50, 50, 4)
        assert np.array_equal(result[0, 0], [128, 128, 128, 255])

    def test_renderer_layer_management(self):
        """Test adding, removing, and clearing layers"""
        renderer = ModernGLRenderer(100, 100)

        layer1 = SolidLayer("layer1", z_order=1, width=100, height=100)
        layer2 = SolidLayer("layer2", z_order=0, width=100, height=100)

        renderer.add_layer(layer1)
        renderer.add_layer(layer2)

        # Should be sorted by z_order
        assert len(renderer.layers) == 2
        assert renderer.layers[0] == layer2  # z_order 0
        assert renderer.layers[1] == layer1  # z_order 1

        renderer.remove_layer(layer1)
        assert len(renderer.layers) == 1
        assert layer1 not in renderer.layers

        renderer.clear_layers()
        assert len(renderer.layers) == 0

    def test_renderer_resize(self):
        """Test renderer resizing"""
        renderer = ModernGLRenderer(100, 100)
        layer = SolidLayer("test", width=100, height=100)
        renderer.add_layer(layer)

        renderer.resize(200, 150)

        assert renderer.get_size() == (200, 150)
        assert layer.get_size() == (200, 150)

    def test_renderer_alpha_blending(self):
        """Test alpha blending between layers"""
        renderer = ModernGLRenderer(100, 100)

        # Background: opaque red
        bg_layer = SolidLayer("bg", (255, 0, 0), 255, z_order=0, width=100, height=100)

        # Foreground: semi-transparent green
        fg_layer = SolidLayer("fg", (0, 255, 0), 128, z_order=1, width=100, height=100)

        renderer.add_layer(bg_layer)
        renderer.add_layer(fg_layer)

        frame = Frame({})
        scheme = ColorScheme(Color("red"), Color("blue"), Color("green"))

        result = renderer.render_frame(frame, scheme)

        assert result is not None
        assert result.shape == (100, 100, 4)

        # Check blending result
        pixel = result[50, 50]
        assert pixel[0] > 0  # Some red from background
        assert pixel[1] > 0  # Some green from foreground
        assert pixel[2] == 0  # No blue
        assert pixel[3] > 200  # High alpha from blending

    def test_renderer_no_layers(self):
        """Test renderer with no layers"""
        renderer = ModernGLRenderer(100, 100)

        frame = Frame({})
        scheme = ColorScheme(Color("red"), Color("blue"), Color("green"))

        result = renderer.render_frame(frame, scheme)

        # Should return None (CPU fallback) or transparent frame (GPU)
        if result is not None:
            assert result.shape == (100, 100, 4)
            # Should be all transparent
            assert np.all(result[:, :, 3] == 0)

    def test_renderer_cleanup(self):
        """Test renderer cleanup"""
        renderer = ModernGLRenderer(100, 100)

        # Add a layer
        layer = SolidLayer("test", width=100, height=100)
        renderer.add_layer(layer)

        # Cleanup should not raise errors
        renderer.cleanup()

        # Should be marked as not initialized
        assert not renderer._initialized

    def test_renderer_error_handling(self):
        """Test error handling in renderer"""
        renderer = ModernGLRenderer(100, 100)

        # Create a layer that might cause issues
        layer = SolidLayer("test", width=100, height=100)

        # Override render to simulate an error
        def error_render(frame, scheme):
            raise RuntimeError("Simulated render error")

        layer.render = error_render
        renderer.add_layer(layer)

        frame = Frame({})
        scheme = ColorScheme(Color("red"), Color("blue"), Color("green"))

        # Should not crash, should fall back gracefully
        result = renderer.render_frame(frame, scheme)

        # Might return None or an empty frame, but shouldn't crash
        if result is not None:
            assert result.shape == (100, 100, 4)
