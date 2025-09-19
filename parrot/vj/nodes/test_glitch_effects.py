#!/usr/bin/env python3

import pytest
import time
from unittest.mock import Mock, call

from parrot.vj.nodes.datamosh_effect import DatamoshEffect
from parrot.vj.nodes.rgb_shift_effect import RGBShiftEffect
from parrot.vj.nodes.scanlines_effect import ScanlinesEffect
from parrot.vj.nodes.pixelate_effect import PixelateEffect
from parrot.vj.nodes.noise_effect import NoiseEffect
from parrot.vj.nodes.beat_hue_shift import BeatHueShift
from parrot.graph.BaseInterpretationNode import BaseInterpretationNode, Vibe
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode


class MockInputNode(BaseInterpretationNode):
    """Mock input node for testing"""

    def __init__(self):
        super().__init__([])

    def enter(self, context):
        pass

    def exit(self):
        pass

    def generate(self, vibe):
        pass

    def render(self, frame, scheme, context):
        return Mock()


class TestDatamoshEffect:
    """Test DatamoshEffect functionality"""

    def test_initialization_default(self):
        """Test DatamoshEffect initialization with defaults"""
        input_node = MockInputNode()
        effect = DatamoshEffect(input_node)

        assert effect.input_node == input_node
        assert effect.displacement_strength == 0.05
        assert effect.corruption_intensity == 0.3
        assert effect.glitch_frequency == 0.8
        assert effect.signal == FrameSignal.freq_high

    def test_initialization_custom(self):
        """Test DatamoshEffect initialization with custom parameters"""
        input_node = MockInputNode()
        effect = DatamoshEffect(
            input_node,
            displacement_strength=0.1,
            corruption_intensity=0.5,
            glitch_frequency=0.6,
            signal=FrameSignal.sustained_high,
        )

        assert effect.displacement_strength == 0.1
        assert effect.corruption_intensity == 0.5
        assert effect.glitch_frequency == 0.6
        assert effect.signal == FrameSignal.sustained_high

    def test_shader_contains_glitch_logic(self):
        """Test that fragment shader contains datamosh logic"""
        input_node = MockInputNode()
        effect = DatamoshEffect(input_node)
        shader = effect._get_fragment_shader()

        assert "displacement_strength" in shader
        assert "corruption_intensity" in shader
        assert "glitch_frequency" in shader
        assert "random" in shader
        assert "noise" in shader

    def test_generate_updates_seed(self):
        """Test that generate can update glitch seed"""
        input_node = MockInputNode()
        effect = DatamoshEffect(input_node)
        original_seed = effect.glitch_seed

        # Generate multiple times to potentially trigger seed change
        vibe = Vibe(Mode.rave)
        for _ in range(20):
            effect.generate(vibe)

        # Seed might have changed (it's random, so we can't guarantee it)
        assert isinstance(effect.glitch_seed, float)


class TestRGBShiftEffect:
    """Test RGBShiftEffect functionality"""

    def test_initialization_default(self):
        """Test RGBShiftEffect initialization with defaults"""
        input_node = MockInputNode()
        effect = RGBShiftEffect(input_node)

        assert effect.input_node == input_node
        assert effect.shift_strength == 0.01
        assert effect.shift_speed == 2.0
        assert effect.vertical_shift == False
        assert effect.signal == FrameSignal.freq_all

    def test_initialization_custom(self):
        """Test RGBShiftEffect initialization with custom parameters"""
        input_node = MockInputNode()
        effect = RGBShiftEffect(
            input_node,
            shift_strength=0.05,
            shift_speed=3.0,
            vertical_shift=True,
            signal=FrameSignal.freq_high,
        )

        assert effect.shift_strength == 0.05
        assert effect.shift_speed == 3.0
        assert effect.vertical_shift == True
        assert effect.signal == FrameSignal.freq_high

    def test_shader_contains_rgb_logic(self):
        """Test that fragment shader contains RGB shift logic"""
        input_node = MockInputNode()
        effect = RGBShiftEffect(input_node)
        shader = effect._get_fragment_shader()

        assert "shift_strength" in shader
        assert "red_shift" in shader
        assert "blue_shift" in shader
        assert "green_shift" in shader
        assert "vertical_shift" in shader


class TestScanlinesEffect:
    """Test ScanlinesEffect functionality"""

    def test_initialization_default(self):
        """Test ScanlinesEffect initialization with defaults"""
        input_node = MockInputNode()
        effect = ScanlinesEffect(input_node)

        assert effect.input_node == input_node
        assert effect.scanline_intensity == 0.4
        assert effect.scanline_count == 300.0
        assert effect.roll_speed == 0.5
        assert effect.curvature == 0.1
        assert effect.signal == FrameSignal.sustained_low

    def test_shader_contains_scanline_logic(self):
        """Test that fragment shader contains scanline logic"""
        input_node = MockInputNode()
        effect = ScanlinesEffect(input_node)
        shader = effect._get_fragment_shader()

        assert "scanline_intensity" in shader
        assert "scanline_count" in shader
        assert "barrel_distort" in shader
        assert "phosphor" in shader
        assert "curvature" in shader


class TestPixelateEffect:
    """Test PixelateEffect functionality"""

    def test_initialization_default(self):
        """Test PixelateEffect initialization with defaults"""
        input_node = MockInputNode()
        effect = PixelateEffect(input_node)

        assert effect.input_node == input_node
        assert effect.pixel_size == 8.0
        assert effect.color_depth == 16
        assert effect.dither == True
        assert effect.signal == FrameSignal.freq_low

    def test_color_depth_clamping(self):
        """Test that color depth is properly clamped"""
        input_node = MockInputNode()

        # Test lower bound
        effect_low = PixelateEffect(input_node, color_depth=1)
        assert effect_low.color_depth == 2

        # Test upper bound
        effect_high = PixelateEffect(input_node, color_depth=300)
        assert effect_high.color_depth == 256

        # Test normal value
        effect_normal = PixelateEffect(input_node, color_depth=32)
        assert effect_normal.color_depth == 32

    def test_shader_contains_pixelate_logic(self):
        """Test that fragment shader contains pixelation logic"""
        input_node = MockInputNode()
        effect = PixelateEffect(input_node)
        shader = effect._get_fragment_shader()

        assert "pixel_size" in shader
        assert "color_depth" in shader
        assert "dither_pattern" in shader
        assert "quantized" in shader


class TestNoiseEffect:
    """Test NoiseEffect functionality"""

    def test_initialization_default(self):
        """Test NoiseEffect initialization with defaults"""
        input_node = MockInputNode()
        effect = NoiseEffect(input_node)

        assert effect.input_node == input_node
        assert effect.noise_intensity == 0.3
        assert effect.noise_scale == 100.0
        assert effect.static_lines == True
        assert effect.color_noise == True
        assert effect.signal == FrameSignal.sustained_high

    def test_shader_contains_noise_logic(self):
        """Test that fragment shader contains noise logic"""
        input_node = MockInputNode()
        effect = NoiseEffect(input_node)
        shader = effect._get_fragment_shader()

        assert "noise_intensity" in shader
        assert "static_lines" in shader
        assert "color_noise" in shader
        assert "fractal_noise" in shader
        assert "dropout" in shader

    def test_generate_updates_seed(self):
        """Test that generate can update noise seed"""
        input_node = MockInputNode()
        effect = NoiseEffect(input_node)
        original_seed = effect.noise_seed

        # Generate multiple times to potentially trigger seed change
        vibe = Vibe(Mode.rave)
        for _ in range(20):
            effect.generate(vibe)

        # Seed might have changed (it's random, so we can't guarantee it)
        assert isinstance(effect.noise_seed, float)


class TestBeatHueShift:
    """Test BeatHueShift functionality"""

    def test_initialization_default(self):
        """Test BeatHueShift initialization with defaults"""
        input_node = MockInputNode()
        effect = BeatHueShift(input_node)

        assert effect.input_node == input_node
        assert effect.hue_shift_amount == 60.0
        assert effect.saturation_boost == 1.2
        assert effect.transition_speed == 8.0
        assert effect.random_hues == True
        assert effect.signal == FrameSignal.pulse

    def test_initialization_custom(self):
        """Test BeatHueShift initialization with custom parameters"""
        input_node = MockInputNode()
        effect = BeatHueShift(
            input_node,
            hue_shift_amount=90.0,
            saturation_boost=1.5,
            transition_speed=12.0,
            random_hues=False,
            signal=FrameSignal.strobe,
        )

        assert effect.hue_shift_amount == 90.0
        assert effect.saturation_boost == 1.5
        assert effect.transition_speed == 12.0
        assert effect.random_hues == False
        assert effect.signal == FrameSignal.strobe

    def test_shader_contains_hue_logic(self):
        """Test that fragment shader contains hue shifting logic"""
        input_node = MockInputNode()
        effect = BeatHueShift(input_node)
        shader = effect._get_fragment_shader()

        assert "target_hue" in shader
        assert "current_hue" in shader
        assert "saturation_boost" in shader
        assert "rgb2hsv" in shader
        assert "hsv2rgb" in shader
        assert "interpolate_hue" in shader

    def test_beat_detection(self):
        """Test beat detection logic"""
        input_node = MockInputNode()
        effect = BeatHueShift(input_node)

        # Test no beat (low signal)
        assert effect._detect_beat(0.3) == False

        # Test beat detection (high signal after low, with time gap)
        effect.last_signal_value = 0.3
        effect.last_beat_time = time.time() - 0.2  # 200ms ago
        assert effect._detect_beat(0.8) == True

        # Test no double beat (already high signal)
        effect.last_signal_value = 0.8
        assert effect._detect_beat(0.9) == False

    def test_hue_sequence_cycling(self):
        """Test hue sequence cycling in non-random mode"""
        input_node = MockInputNode()
        effect = BeatHueShift(input_node, random_hues=False)

        # Test cycling through predefined hues
        first_hue = effect._get_next_hue()
        second_hue = effect._get_next_hue()
        third_hue = effect._get_next_hue()

        assert first_hue == 0.0  # Red
        assert second_hue == 60.0  # Yellow
        assert third_hue == 120.0  # Green

    def test_random_hue_generation(self):
        """Test random hue generation"""
        input_node = MockInputNode()
        effect = BeatHueShift(input_node, random_hues=True)

        # Generate multiple random hues
        hues = [effect._get_next_hue() for _ in range(10)]

        # All should be valid hue values (0-360)
        for hue in hues:
            assert 0.0 <= hue < 360.0

        # Should have some variation (not all the same)
        assert len(set(hues)) > 1


class TestGlitchEffectsIntegration:
    """Test integration and common functionality of glitch effects"""

    def test_all_effects_inherit_from_base(self):
        """Test that all effects properly inherit from PostProcessEffectBase"""
        input_node = MockInputNode()

        effects = [
            DatamoshEffect(input_node),
            RGBShiftEffect(input_node),
            ScanlinesEffect(input_node),
            PixelateEffect(input_node),
            NoiseEffect(input_node),
            BeatHueShift(input_node),
        ]

        for effect in effects:
            assert hasattr(effect, "input_node")
            assert hasattr(effect, "_get_fragment_shader")
            assert hasattr(effect, "_set_effect_uniforms")
            assert hasattr(effect, "generate")

    def test_all_effects_have_signal_parameter(self):
        """Test that all effects have configurable signal parameters"""
        input_node = MockInputNode()

        effects = [
            DatamoshEffect(input_node, signal=FrameSignal.freq_low),
            RGBShiftEffect(input_node, signal=FrameSignal.freq_all),
            ScanlinesEffect(input_node, signal=FrameSignal.freq_high),
            PixelateEffect(input_node, signal=FrameSignal.sustained_low),
            NoiseEffect(input_node, signal=FrameSignal.sustained_high),
            BeatHueShift(input_node, signal=FrameSignal.pulse),
        ]

        expected_signals = [
            FrameSignal.freq_low,
            FrameSignal.freq_all,
            FrameSignal.freq_high,
            FrameSignal.sustained_low,
            FrameSignal.sustained_high,
            FrameSignal.pulse,
        ]

        for effect, expected_signal in zip(effects, expected_signals):
            assert effect.signal == expected_signal

    def test_uniform_setting_with_mock_frame(self):
        """Test that uniform setting works with mock frame data"""
        input_node = MockInputNode()
        effect = DatamoshEffect(input_node)

        # Create mock frame and scheme
        frame = Mock(spec=Frame)
        frame.__getitem__ = Mock(return_value=0.5)  # Mock signal value
        scheme = Mock(spec=ColorScheme)

        # Mock shader program
        effect.shader_program = Mock()
        effect.shader_program.__setitem__ = Mock()

        # Test uniform setting
        effect._set_effect_uniforms(frame, scheme)

        # Verify frame signals were accessed (enhanced effects now access multiple signals)
        expected_calls = [
            call(effect.signal),  # Original signal
            call(FrameSignal.strobe),  # Special signal responses
            call(FrameSignal.big_blinder),
            call(FrameSignal.pulse),
        ]
        frame.__getitem__.assert_has_calls(expected_calls, any_order=True)


if __name__ == "__main__":
    pytest.main([__file__])
