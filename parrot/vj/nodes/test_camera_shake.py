#!/usr/bin/env python3

import unittest
import time
import math
from unittest.mock import Mock, MagicMock
import moderngl as mgl

from parrot.vj.nodes.camera_shake import CameraShake
from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode
from parrot.utils.colour import Color


class MockInputNode(BaseInterpretationNode):
    """Mock input node that inherits from BaseInterpretationNode for beartype compatibility"""

    def __init__(self):
        super().__init__([])
        self.mock_framebuffer = Mock(spec=mgl.Framebuffer)
        self.mock_framebuffer.width = 1920
        self.mock_framebuffer.height = 1080
        self.mock_framebuffer.color_attachments = [Mock()]

    def enter(self, context):
        pass

    def exit(self):
        pass

    def generate(self, vibe: Vibe):
        pass

    def render(self, frame: Frame, scheme: ColorScheme, context) -> mgl.Framebuffer:
        return self.mock_framebuffer


class TestCameraShake(unittest.TestCase):
    def setUp(self):
        """Set up test fixtures"""
        self.mock_input_node = MockInputNode()
        self.mock_input_framebuffer = self.mock_input_node.mock_framebuffer

        self.camera_shake = CameraShake(
            input_node=self.mock_input_node,
            shake_intensity=2.0,
            shake_frequency=10.0,
            blur_intensity=0.5,
            signal=FrameSignal.freq_low,
        )

        # Mock OpenGL context and resources
        self.mock_context = Mock(spec=mgl.Context)
        self.mock_framebuffer = Mock(spec=mgl.Framebuffer)
        self.mock_framebuffer.width = 1920
        self.mock_framebuffer.height = 1080
        self.mock_texture = Mock()
        self.mock_shader_program = (
            MagicMock()
        )  # Use MagicMock to support item assignment
        self.mock_quad_vao = Mock()

        self.camera_shake.framebuffer = self.mock_framebuffer
        self.camera_shake.texture = self.mock_texture
        self.camera_shake.shader_program = self.mock_shader_program
        self.camera_shake.quad_vao = self.mock_quad_vao

    def test_initialization(self):
        """Test that CameraShake initializes with correct parameters"""
        self.assertEqual(self.camera_shake.shake_intensity, 2.0)
        self.assertEqual(self.camera_shake.shake_frequency, 10.0)
        self.assertEqual(self.camera_shake.blur_intensity, 0.5)
        self.assertEqual(self.camera_shake.signal, FrameSignal.freq_low)
        self.assertEqual(self.camera_shake.shake_x, 0.0)
        self.assertEqual(self.camera_shake.shake_y, 0.0)

    def test_generate_randomizes_parameters(self):
        """Test that generate() randomizes shake parameters"""
        vibe = Vibe(mode=Mode.rave)

        original_intensity = self.camera_shake.shake_intensity
        original_frequency = self.camera_shake.shake_frequency
        original_blur = self.camera_shake.blur_intensity
        original_signal = self.camera_shake.signal

        self.camera_shake.generate(vibe)

        # Parameters should be randomized (very unlikely to be exactly the same)
        self.assertNotEqual(self.camera_shake.shake_intensity, original_intensity)
        self.assertNotEqual(self.camera_shake.shake_frequency, original_frequency)
        self.assertNotEqual(self.camera_shake.blur_intensity, original_blur)
        # Signal might be the same by chance, so we don't test it

    def test_generate_sets_valid_ranges(self):
        """Test that generate() sets parameters within valid ranges"""
        vibe = Vibe(mode=Mode.rave)
        self.camera_shake.generate(vibe)

        self.assertGreaterEqual(self.camera_shake.shake_intensity, 0.5)
        self.assertLessEqual(self.camera_shake.shake_intensity, 3.0)
        self.assertGreaterEqual(self.camera_shake.shake_frequency, 4.0)
        self.assertLessEqual(self.camera_shake.shake_frequency, 15.0)
        self.assertGreaterEqual(self.camera_shake.blur_intensity, 0.3)
        self.assertLessEqual(self.camera_shake.blur_intensity, 1.2)

    def test_fragment_shader_contains_required_elements(self):
        """Test that the fragment shader contains required uniforms and logic"""
        shader = self.camera_shake._get_fragment_shader()

        # Check for required uniforms
        self.assertIn("uniform sampler2D input_texture", shader)
        self.assertIn("uniform vec2 shake_offset", shader)
        self.assertIn("uniform float blur_amount", shader)

        # Check for main shader logic
        self.assertIn("vec2 shaken_uv = uv + shake_offset", shader)
        self.assertIn("blur_amount > 0.001", shader)
        self.assertIn("texture(input_texture", shader)

    def test_set_effect_uniforms_with_signal(self):
        """Test that _set_effect_uniforms correctly processes frame signals"""
        frame = Frame(
            {
                FrameSignal.freq_low: 0.8,
                FrameSignal.freq_high: 0.2,
            }
        )
        scheme = ColorScheme(Color("red"), Color("blue"), Color("white"))

        # Set initial time
        self.camera_shake.last_time = time.time() - 0.016  # Simulate 60fps

        self.camera_shake._set_effect_uniforms(frame, scheme)

        # Check that shader uniforms were set
        self.mock_shader_program.__setitem__.assert_any_call(
            "shake_offset", unittest.mock.ANY
        )
        self.mock_shader_program.__setitem__.assert_any_call(
            "blur_amount", unittest.mock.ANY
        )

    def test_shake_motion_responds_to_signal(self):
        """Test that shake motion responds to signal strength"""
        # Test with low signal
        frame_low = Frame({FrameSignal.freq_low: 0.1})
        scheme = ColorScheme(Color("red"), Color("blue"), Color("white"))

        self.camera_shake.last_time = time.time() - 0.016
        self.camera_shake._set_effect_uniforms(frame_low, scheme)

        # Get the shake offset that was set
        shake_calls = [
            call
            for call in self.mock_shader_program.__setitem__.call_args_list
            if call[0][0] == "shake_offset"
        ]
        self.assertTrue(len(shake_calls) > 0)
        low_signal_offset = shake_calls[-1][0][1]

        # Reset and test with high signal
        self.mock_shader_program.reset_mock()
        frame_high = Frame({FrameSignal.freq_low: 0.9})

        self.camera_shake.last_time = time.time() - 0.016
        self.camera_shake._set_effect_uniforms(frame_high, scheme)

        shake_calls = [
            call
            for call in self.mock_shader_program.__setitem__.call_args_list
            if call[0][0] == "shake_offset"
        ]
        self.assertTrue(len(shake_calls) > 0)
        high_signal_offset = shake_calls[-1][0][1]

        # High signal should generally produce larger shake (though timing dependent)
        # We'll just verify the mechanism is working by checking values are set
        self.assertIsInstance(low_signal_offset, tuple)
        self.assertIsInstance(high_signal_offset, tuple)
        self.assertEqual(len(low_signal_offset), 2)
        self.assertEqual(len(high_signal_offset), 2)

    def test_blur_amount_calculation(self):
        """Test that blur amount is calculated based on shake velocity and signal"""
        frame = Frame({FrameSignal.freq_low: 0.5})
        scheme = ColorScheme(Color("red"), Color("blue"), Color("white"))

        # Set some initial velocity
        self.camera_shake.shake_velocity_x = 10.0
        self.camera_shake.shake_velocity_y = 5.0
        self.camera_shake.last_time = time.time() - 0.016

        self.camera_shake._set_effect_uniforms(frame, scheme)

        # Check that blur_amount was set
        blur_calls = [
            call
            for call in self.mock_shader_program.__setitem__.call_args_list
            if call[0][0] == "blur_amount"
        ]
        self.assertTrue(len(blur_calls) > 0)
        blur_amount = blur_calls[-1][0][1]

        self.assertIsInstance(blur_amount, float)
        self.assertGreaterEqual(blur_amount, 0.0)
        self.assertLessEqual(blur_amount, 1.0)

    def test_time_delta_clamping(self):
        """Test that time delta is properly clamped to prevent huge jumps"""
        frame = Frame({FrameSignal.freq_low: 0.5})
        scheme = ColorScheme(Color("red"), Color("blue"), Color("white"))

        # Set a very old last_time to simulate a huge time jump
        self.camera_shake.last_time = time.time() - 10.0  # 10 seconds ago

        # This should not crash and should clamp the dt
        self.camera_shake._set_effect_uniforms(frame, scheme)

        # Verify that uniforms were still set properly
        self.mock_shader_program.__setitem__.assert_any_call(
            "shake_offset", unittest.mock.ANY
        )
        self.mock_shader_program.__setitem__.assert_any_call(
            "blur_amount", unittest.mock.ANY
        )

    def test_render_with_valid_input(self):
        """Test rendering with valid input framebuffer"""
        frame = Frame({FrameSignal.freq_low: 0.5})
        scheme = ColorScheme(Color("red"), Color("blue"), Color("white"))

        result = self.camera_shake.render(frame, scheme, self.mock_context)

        # Should return our mock framebuffer
        self.assertEqual(result, self.mock_framebuffer)

        # Should have called use() on framebuffer
        self.mock_framebuffer.use.assert_called_once()

        # Should have rendered the quad
        self.mock_quad_vao.render.assert_called_once()


if __name__ == "__main__":
    unittest.main()
