import pytest
import numpy as np
from parrot.vj.base import LayerBase, VJInterpreterBase, SolidLayer
from parrot.vj.renderer import ModernGLRenderer as VJRenderer
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.interpreters.base import InterpreterArgs
from parrot.utils.colour import Color


class MockLayer(LayerBase):
    """Mock layer for testing"""

    def __init__(self, name="mock", color=(255, 0, 0), alpha=255, z_order=0):
        super().__init__(name, z_order, 100, 100)
        self.color = color
        self.layer_alpha = alpha

    def render(self, frame, scheme):
        if not self.enabled:
            return None

        # Create a simple colored rectangle
        texture = np.full(
            (self.height, self.width, 4),
            (*self.color, self.layer_alpha),
            dtype=np.uint8,
        )
        return texture


class MockInterpreter(VJInterpreterBase):
    """Mock interpreter for testing"""

    def __init__(self, layers, args):
        super().__init__(layers, args)
        self.step_called = False

    def step(self, frame, scheme):
        self.step_called = True


class TestLayerBase:
    """Test the base layer functionality"""

    def test_layer_creation(self):
        layer = MockLayer("test_layer", (255, 128, 64), 200, 5)
        assert layer.name == "test_layer"
        assert layer.z_order == 5
        assert layer.alpha == 1.0
        assert layer.enabled == True
        assert layer.get_size() == (100, 100)

    def test_layer_alpha_control(self):
        layer = MockLayer()

        # Test alpha setting
        layer.set_alpha(0.5)
        assert layer.get_alpha() == 0.5

        # Test alpha clamping
        layer.set_alpha(-0.1)
        assert layer.get_alpha() == 0.0

        layer.set_alpha(1.5)
        assert layer.get_alpha() == 1.0

    def test_layer_enable_disable(self):
        layer = MockLayer()

        assert layer.is_enabled() == True

        layer.set_enabled(False)
        assert layer.is_enabled() == False

        layer.set_enabled(True)
        assert layer.is_enabled() == True

    def test_layer_resize(self):
        layer = MockLayer()

        layer.resize(200, 150)
        assert layer.get_size() == (200, 150)

    def test_layer_render(self):
        layer = MockLayer("test", (255, 128, 64), 200)
        frame = Frame({})
        scheme = ColorScheme(Color("red"), Color("blue"), Color("green"))

        result = layer.render(frame, scheme)

        assert result is not None
        assert result.shape == (100, 100, 4)
        assert result.dtype == np.uint8
        assert np.array_equal(result[0, 0], [255, 128, 64, 200])

    def test_layer_render_disabled(self):
        layer = MockLayer()
        layer.set_enabled(False)

        frame = Frame({})
        scheme = ColorScheme(Color("red"), Color("blue"), Color("green"))

        result = layer.render(frame, scheme)
        assert result is None


class TestVJInterpreterBase:
    """Test the base VJ interpreter functionality"""

    def test_interpreter_creation(self):
        layers = [MockLayer()]
        args = InterpreterArgs(50, True, 0, 100)

        interpreter = MockInterpreter(layers, args)

        assert interpreter.layers == layers
        assert interpreter.interpreter_args == args
        assert interpreter.get_hype() == 0  # Default hype

    def test_interpreter_step(self):
        layers = [MockLayer()]
        args = InterpreterArgs(50, True, 0, 100)
        interpreter = MockInterpreter(layers, args)

        frame = Frame({})
        scheme = ColorScheme(Color("red"), Color("blue"), Color("green"))

        assert interpreter.step_called == False
        interpreter.step(frame, scheme)
        assert interpreter.step_called == True


class TestVJRenderer:
    """Test the VJ renderer functionality"""

    def test_renderer_creation(self):
        renderer = VJRenderer(800, 600)

        assert renderer.width == 800
        assert renderer.height == 600
        assert len(renderer.layers) == 0
        assert renderer.get_size() == (800, 600)

    def test_renderer_layer_management(self):
        renderer = VJRenderer(100, 100)

        layer1 = MockLayer("layer1", z_order=1)
        layer2 = MockLayer("layer2", z_order=0)
        layer3 = MockLayer("layer3", z_order=2)

        renderer.add_layer(layer1)
        renderer.add_layer(layer2)
        renderer.add_layer(layer3)

        # Layers should be sorted by z_order
        assert len(renderer.layers) == 3
        assert renderer.layers[0] == layer2  # z_order 0
        assert renderer.layers[1] == layer1  # z_order 1
        assert renderer.layers[2] == layer3  # z_order 2

        renderer.remove_layer(layer1)
        assert len(renderer.layers) == 2
        assert layer1 not in renderer.layers

        renderer.clear_layers()
        assert len(renderer.layers) == 0

    def test_renderer_single_layer(self):
        renderer = VJRenderer(100, 100)
        layer = MockLayer("test", (255, 0, 0), 255)
        renderer.add_layer(layer)

        frame = Frame({})
        scheme = ColorScheme(Color("red"), Color("blue"), Color("green"))

        result = renderer.render_frame(frame, scheme)

        assert result is not None
        assert result.shape == (100, 100, 4)
        assert result.dtype == np.uint8
        # Should be solid red
        assert np.array_equal(result[0, 0], [255, 0, 0, 255])

    def test_renderer_no_layers(self):
        renderer = VJRenderer(100, 100)

        frame = Frame({})
        scheme = ColorScheme(Color("red"), Color("blue"), Color("green"))

        result = renderer.render_frame(frame, scheme)
        assert result is None

    def test_renderer_disabled_layer(self):
        renderer = VJRenderer(100, 100)
        layer = MockLayer("test", (255, 0, 0), 255)
        layer.set_enabled(False)
        renderer.add_layer(layer)

        frame = Frame({})
        scheme = ColorScheme(Color("red"), Color("blue"), Color("green"))

        result = renderer.render_frame(frame, scheme)
        # With ModernGL renderer, disabled layers result in transparent black frame
        if result is not None:
            # Should be all transparent (alpha = 0)
            assert np.all(result[:, :, 3] == 0)  # All alpha values should be 0
        else:
            # CPU fallback might return None
            assert result is None

    def test_renderer_alpha_blending(self):
        renderer = VJRenderer(100, 100)

        # Background layer (opaque red)
        bg_layer = MockLayer("bg", (255, 0, 0), 255, z_order=0)

        # Foreground layer (semi-transparent green)
        fg_layer = MockLayer("fg", (0, 255, 0), 128, z_order=1)

        renderer.add_layer(bg_layer)
        renderer.add_layer(fg_layer)

        frame = Frame({})
        scheme = ColorScheme(Color("red"), Color("blue"), Color("green"))

        result = renderer.render_frame(frame, scheme)

        assert result is not None
        assert result.shape == (100, 100, 4)

        # Should be a blend of red and green
        pixel = result[0, 0]
        assert pixel[0] > 0  # Some red
        assert pixel[1] > 0  # Some green
        assert pixel[2] == 0  # No blue
        assert pixel[3] == 255  # Full alpha

    def test_renderer_layer_alpha_control(self):
        renderer = VJRenderer(100, 100)
        layer = MockLayer("test", (255, 0, 0), 255)
        layer.set_alpha(0.5)  # 50% transparent
        renderer.add_layer(layer)

        frame = Frame({})
        scheme = ColorScheme(Color("red"), Color("blue"), Color("green"))

        result = renderer.render_frame(frame, scheme)

        assert result is not None
        # The layer alpha should affect the final result
        pixel = result[0, 0]
        assert pixel[3] < 255  # Should be less than fully opaque

    def test_renderer_resize(self):
        renderer = VJRenderer(100, 100)
        layer = MockLayer()
        renderer.add_layer(layer)

        renderer.resize(200, 150)

        assert renderer.get_size() == (200, 150)
        assert layer.get_size() == (200, 150)  # Layer should also be resized


class TestSolidLayer:
    """Test the solid layer implementation"""

    def test_solid_layer_creation(self):
        layer = SolidLayer("solid", (128, 64, 32), 200, z_order=3, width=50, height=40)

        assert layer.name == "solid"
        assert layer.color == (128, 64, 32)
        assert layer.layer_alpha == 200
        assert layer.z_order == 3
        assert layer.get_size() == (50, 40)

    def test_solid_layer_render(self):
        layer = SolidLayer("test", (100, 150, 200), 180, width=10, height=8)

        frame = Frame({})
        scheme = ColorScheme(Color("red"), Color("blue"), Color("green"))

        result = layer.render(frame, scheme)

        assert result is not None
        assert result.shape == (8, 10, 4)
        assert np.all(result == [100, 150, 200, 180])

    def test_solid_layer_color_change(self):
        layer = SolidLayer("test", (255, 0, 0), 255)

        layer.set_color((0, 255, 0))
        assert layer.color == (0, 255, 0)

        layer.set_layer_alpha(128)
        assert layer.layer_alpha == 128

    def test_solid_layer_disabled(self):
        layer = SolidLayer()
        layer.set_enabled(False)

        frame = Frame({})
        scheme = ColorScheme(Color("red"), Color("blue"), Color("green"))

        result = layer.render(frame, scheme)
        assert result is None
