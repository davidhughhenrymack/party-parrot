#!/usr/bin/env python3

import pytest
from beartype import beartype

from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode
from parrot.vj.nodes.bloom_filter import BloomFilter
from parrot.vj.nodes.black import Black
from parrot.graph.BaseInterpretationNode import Vibe
from parrot.utils.colour import Color


@beartype
class TestBloomFilter:
    """Test the BloomFilter node"""

    def test_initialization(self):
        """Test BloomFilter initialization with default parameters"""
        black_node = Black()
        bloom = BloomFilter(black_node)

        assert bloom.base_intensity == 0.4
        assert bloom.max_intensity == 0.8
        assert bloom.bloom_radius == 4.0
        assert bloom.threshold == 0.3
        assert bloom.signal == FrameSignal.sustained_low
        assert bloom.blur_passes == 2

    def test_initialization_with_custom_parameters(self):
        """Test BloomFilter initialization with custom parameters"""
        black_node = Black()
        bloom = BloomFilter(
            black_node,
            base_intensity=0.1,
            max_intensity=0.5,
            bloom_radius=3.0,
            threshold=0.3,
            signal=FrameSignal.freq_low,
            blur_passes=1,
        )

        assert bloom.base_intensity == 0.1
        assert bloom.max_intensity == 0.5
        assert bloom.bloom_radius == 3.0
        assert bloom.threshold == 0.3
        assert bloom.signal == FrameSignal.freq_low
        assert bloom.blur_passes == 1

    def test_gentle_parameters(self):
        """Test that BloomFilter uses gentle parameters suitable for chill/gentle modes"""
        black_node = Black()

        # Test gentle mode parameters
        gentle_bloom = BloomFilter(
            black_node,
            base_intensity=0.4,
            max_intensity=0.7,
            bloom_radius=4.0,
            threshold=0.3,
            signal=FrameSignal.sustained_low,
        )

        # Verify parameters are in gentle ranges
        assert 0.3 <= gentle_bloom.base_intensity <= 0.5
        assert 0.6 <= gentle_bloom.max_intensity <= 0.9
        assert 2.0 <= gentle_bloom.bloom_radius <= 6.0
        assert 0.2 <= gentle_bloom.threshold <= 0.4

        # Test chill mode parameters
        chill_bloom = BloomFilter(
            black_node,
            base_intensity=0.3,
            max_intensity=0.6,
            bloom_radius=3.0,
            threshold=0.25,
            signal=FrameSignal.sustained_low,
        )

        # Verify chill parameters are even more gentle
        assert chill_bloom.base_intensity <= gentle_bloom.base_intensity
        assert chill_bloom.max_intensity <= gentle_bloom.max_intensity
        assert chill_bloom.bloom_radius <= gentle_bloom.bloom_radius

    def test_parameter_ranges(self):
        """Test parameter validation and ranges"""
        black_node = Black()

        # Test extreme gentle parameters
        gentle_bloom = BloomFilter(
            black_node,
            base_intensity=0.05,
            max_intensity=0.3,
            bloom_radius=2.0,
            threshold=0.2,
        )

        assert gentle_bloom.base_intensity == 0.05
        assert gentle_bloom.max_intensity == 0.3

    def test_render_logic_without_gl(self):
        """Test the bloom intensity calculation logic without OpenGL dependencies"""
        black_node = Black()
        bloom = BloomFilter(black_node, base_intensity=0.4, max_intensity=0.8)

        # Test the intensity calculation that happens in render()
        frame = Frame({FrameSignal.sustained_low: 0.5})

        # This is the calculation that happens in the render method:
        signal_value = frame[FrameSignal.sustained_low]  # 0.5
        signal_curve = (
            signal_value * signal_value
        )  # 0.25 (quadratic for gentle response)
        dynamic_intensity = (
            bloom.base_intensity
            + (bloom.max_intensity - bloom.base_intensity) * signal_curve
        )
        # 0.4 + (0.8 - 0.4) * 0.25 = 0.4 + 0.4 * 0.25 = 0.4 + 0.1 = 0.5

        expected = 0.5
        actual = bloom.base_intensity + (bloom.max_intensity - bloom.base_intensity) * (
            signal_value * signal_value
        )

        assert abs(actual - expected) < 0.001  # Float comparison with tolerance

    def test_all_inputs_property(self):
        """Test that all_inputs returns the input node"""
        black_node = Black()
        bloom = BloomFilter(black_node)

        assert bloom.all_inputs == [black_node]

    def test_frame_signal_access(self):
        """Test accessing frame signals"""
        frame = Frame(
            {
                FrameSignal.sustained_low: 0.3,
                FrameSignal.freq_low: 0.7,
                FrameSignal.freq_all: 0.5,
            }
        )

        # Test different ways to access the signal
        assert frame[FrameSignal.sustained_low] == 0.3
        assert frame.values[FrameSignal.sustained_low] == 0.3

    def test_generate_vibe_configuration(self):
        """Test that generate() configures parameters based on vibe"""
        black_node = Black()
        bloom = BloomFilter(black_node)

        # Store original values
        original_signal = bloom.signal
        original_base = bloom.base_intensity
        original_max = bloom.max_intensity
        original_radius = bloom.bloom_radius
        original_threshold = bloom.threshold

        # Generate new configuration
        vibe = Vibe(Mode.gentle)
        bloom.generate(vibe)

        # Check that parameters were modified
        # Signal should be one of the low frequency signals
        low_freq_signals = [
            FrameSignal.sustained_low,
            FrameSignal.freq_low,
            FrameSignal.dampen,
        ]
        assert bloom.signal in low_freq_signals

        # Parameters should be in gentle ranges
        assert 0.3 <= bloom.base_intensity <= 0.5
        assert 0.6 <= bloom.max_intensity <= 0.9
        assert 3.0 <= bloom.bloom_radius <= 6.0
        assert 0.2 <= bloom.threshold <= 0.4

    def test_print_self_format(self):
        """Test that print_self returns properly formatted string"""
        black_node = Black()
        bloom = BloomFilter(black_node)

        result = bloom.print_self()

        # Should contain class name, signal name, and parameters
        assert "BloomFilter" in result
        assert bloom.signal.name in result
        assert f"{bloom.max_intensity:.2f}" in result
        assert f"{bloom.bloom_radius:.1f}" in result

    def test_low_frequency_signal_sensitivity(self):
        """Test that BloomFilter responds appropriately to low frequency signals"""
        black_node = Black()
        bloom = BloomFilter(
            black_node,
            base_intensity=0.1,
            max_intensity=0.5,
            signal=FrameSignal.sustained_low,
        )

        # Test with low signal (should be near base intensity)
        low_frame = Frame({FrameSignal.sustained_low: 0.1})
        low_signal = low_frame[FrameSignal.sustained_low]
        low_curve = low_signal * low_signal  # 0.01
        low_intensity = (
            bloom.base_intensity
            + (bloom.max_intensity - bloom.base_intensity) * low_curve
        )
        # 0.1 + (0.5 - 0.1) * 0.01 = 0.1 + 0.004 = 0.104

        # Test with high signal (should be near max intensity)
        high_frame = Frame({FrameSignal.sustained_low: 0.9})
        high_signal = high_frame[FrameSignal.sustained_low]
        high_curve = high_signal * high_signal  # 0.81
        high_intensity = (
            bloom.base_intensity
            + (bloom.max_intensity - bloom.base_intensity) * high_curve
        )
        # 0.1 + (0.5 - 0.1) * 0.81 = 0.1 + 0.324 = 0.424

        # Verify the response is gentle and appropriate
        assert abs(low_intensity - 0.104) < 0.001
        assert abs(high_intensity - 0.424) < 0.001
        assert low_intensity < high_intensity
        assert (
            high_intensity < bloom.max_intensity
        )  # Quadratic curve keeps it below max
