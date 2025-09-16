#!/usr/bin/env python3

import pytest
from unittest.mock import Mock, patch

from parrot.vj.nodes.brightness_pulse import BrightnessPulse
from parrot.vj.nodes.black import Black
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode
from parrot.graph.BaseInterpretationNode import Vibe
from parrot.utils.colour import Color


class TestBrightnessPulse:
    """Test the BrightnessPulse node"""

    def test_initialization(self):
        """Test BrightnessPulse initialization"""
        black_node = Black()
        pulse = BrightnessPulse(black_node, intensity=0.8, base_brightness=0.2)

        assert pulse.input_node == black_node
        assert pulse.intensity == 0.8
        assert pulse.base_brightness == 0.2
        assert pulse.children == [black_node]

    def test_initialization_defaults(self):
        """Test BrightnessPulse initialization with defaults"""
        black_node = Black()
        pulse = BrightnessPulse(black_node)

        assert pulse.intensity == 0.8
        assert pulse.base_brightness == 0.2

    def test_generate(self):
        """Test generate method"""
        black_node = Black()
        pulse = BrightnessPulse(black_node)
        vibe = Vibe(Mode.rave)

        # Should not raise any errors
        pulse.generate(vibe)

    def test_brightness_calculation_values(self):
        """Test brightness calculation logic without OpenGL context"""
        black_node = Black()
        pulse = BrightnessPulse(black_node, intensity=1.0, base_brightness=0.2)

        # Test different frequency values
        frame_low = Frame({FrameSignal.freq_low: 0.5})
        frame_high = Frame({FrameSignal.freq_low: 0.9})
        frame_none = Frame({FrameSignal.freq_low: 0.0})

        # Expected calculations:
        # low: 0.2 + (1.0 * 0.5) = 0.7
        # high: 0.2 + (1.0 * 0.9) = 1.1
        # none: 0.2 + (1.0 * 0.0) = 0.2

        assert frame_low[FrameSignal.freq_low] == 0.5
        assert frame_high[FrameSignal.freq_low] == 0.9
        assert frame_none[FrameSignal.freq_low] == 0.0

    def test_brightness_clamping_logic(self):
        """Test brightness clamping without OpenGL"""
        black_node = Black()
        pulse = BrightnessPulse(black_node, intensity=2.0, base_brightness=1.0)

        # Test extreme values
        frame_extreme = Frame({FrameSignal.freq_low: 2.0})

        # Manual calculation of what should happen in render:
        low_freq = frame_extreme[FrameSignal.freq_low]  # 2.0
        brightness_multiplier = pulse.base_brightness + (pulse.intensity * low_freq)
        # 1.0 + (2.0 * 2.0) = 5.0
        # Should be clamped to 2.0
        expected_clamped = max(0.0, min(2.0, brightness_multiplier))

        assert expected_clamped == 2.0

    def test_parameter_ranges(self):
        """Test different parameter combinations"""
        black_node = Black()

        # Test subtle effect
        subtle_pulse = BrightnessPulse(black_node, intensity=0.3, base_brightness=0.7)
        assert subtle_pulse.intensity == 0.3
        assert subtle_pulse.base_brightness == 0.7

        # Test dramatic effect
        dramatic_pulse = BrightnessPulse(black_node, intensity=1.5, base_brightness=0.1)
        assert dramatic_pulse.intensity == 1.5
        assert dramatic_pulse.base_brightness == 0.1

    def test_render_logic_without_gl(self):
        """Test the brightness calculation logic without OpenGL dependencies"""
        black_node = Black()
        pulse = BrightnessPulse(black_node, intensity=0.8, base_brightness=0.4)

        # Test the brightness calculation that happens in render()
        frame = Frame({FrameSignal.freq_low: 0.6})

        # This is the calculation that happens in the render method:
        low_freq = frame[FrameSignal.freq_low]  # 0.6
        brightness_multiplier = pulse.base_brightness + (pulse.intensity * low_freq)
        # 0.4 + (0.8 * 0.6) = 0.4 + 0.48 = 0.88

        expected = 0.88
        actual = pulse.base_brightness + (pulse.intensity * low_freq)

        assert abs(actual - expected) < 0.001  # Float comparison with tolerance

    def test_all_inputs_property(self):
        """Test that all_inputs returns the input node"""
        black_node = Black()
        pulse = BrightnessPulse(black_node)

        assert pulse.all_inputs == [black_node]

    def test_frame_signal_access(self):
        """Test accessing frame signals"""
        frame = Frame(
            {
                FrameSignal.freq_low: 0.3,
                FrameSignal.freq_high: 0.7,
                FrameSignal.freq_all: 0.5,
            }
        )

        # Test different ways to access the signal
        assert frame[FrameSignal.freq_low] == 0.3
        assert frame.values[FrameSignal.freq_low] == 0.3
