#!/usr/bin/env python3

import unittest
from unittest.mock import patch
from beartype import beartype

from parrot.graph.BaseInterpretationNode import Vibe
from parrot.director.mode import Mode
from parrot.director.frame import FrameSignal
from parrot.vj.nodes.static_color import StaticColor

# Import all effect classes that support signal randomization
from parrot.vj.nodes.brightness_pulse import BrightnessPulse
from parrot.vj.nodes.saturation_pulse import SaturationPulse
from parrot.vj.nodes.camera_zoom import CameraZoom
from parrot.vj.nodes.noise_effect import NoiseEffect
from parrot.vj.nodes.beat_hue_shift import BeatHueShift
from parrot.vj.nodes.rgb_shift_effect import RGBShiftEffect
from parrot.vj.nodes.datamosh_effect import DatamoshEffect
from parrot.vj.nodes.scanlines_effect import ScanlinesEffect
from parrot.vj.nodes.pixelate_effect import PixelateEffect
from parrot.vj.nodes.volumetric_beam import VolumetricBeam
from parrot.vj.nodes.laser_array import LaserArray
from parrot.vj.nodes.oscilloscope_effect import OscilloscopeEffect
from parrot.vj.utils.signal_utils import get_random_frame_signal


class TestSignalRandomization(unittest.TestCase):
    """Test signal randomization functionality for VJ effects"""

    def setUp(self):
        """Set up test fixtures"""
        self.input_node = StaticColor(color=(1.0, 0.0, 0.0))
        self.vibe = Vibe(mode=Mode.rave)

        # Define all effect classes and their initialization requirements
        self.effect_classes = [
            # Effects that need input nodes
            (BrightnessPulse, True),
            (SaturationPulse, True),
            (CameraZoom, True),
            (NoiseEffect, True),
            (BeatHueShift, True),
            (RGBShiftEffect, True),
            (DatamoshEffect, True),
            (ScanlinesEffect, True),
            (PixelateEffect, True),
            # Effects that don't need input nodes
            (VolumetricBeam, False),
            (LaserArray, False),
            (OscilloscopeEffect, False),
        ]

    def test_get_random_frame_signal_utility(self):
        """Test the utility function returns valid FrameSignal values"""
        # Test multiple calls to ensure randomness
        signals = set()
        for _ in range(50):  # Run enough times to likely get different values
            signal = get_random_frame_signal()
            self.assertIsInstance(signal, FrameSignal)
            signals.add(signal)

        # Should have gotten at least a few different signals
        self.assertGreater(len(signals), 1, "Should generate different signals")

        # All signals should be valid FrameSignal enum values
        valid_signals = set(FrameSignal)
        self.assertTrue(
            signals.issubset(valid_signals),
            "All signals should be valid FrameSignal values",
        )

    def test_all_effects_have_signal_randomization(self):
        """Test that all effect classes can randomize their signals"""
        for effect_class, needs_input in self.effect_classes:
            with self.subTest(effect_class=effect_class.__name__):
                # Create effect instance
                if needs_input:
                    effect = effect_class(self.input_node)
                else:
                    effect = effect_class()

                # Store original signal
                original_signal = effect.signal
                self.assertIsInstance(original_signal, FrameSignal)

                # Call generate to trigger randomization
                effect.generate(self.vibe)

                # Verify new signal is valid
                new_signal = effect.signal
                self.assertIsInstance(new_signal, FrameSignal)

    def test_signal_randomization_changes_values(self):
        """Test that signal randomization actually changes values over multiple calls"""
        # Test with BrightnessPulse as representative example
        effect = BrightnessPulse(self.input_node)

        signals = set()
        for _ in range(20):  # Multiple calls should produce different signals
            effect.generate(self.vibe)
            signals.add(effect.signal)

        # Should get at least 2 different signals over 20 calls (very high probability)
        self.assertGreater(
            len(signals), 1, "Signal randomization should produce different values"
        )

    def test_signal_randomization_with_different_vibes(self):
        """Test signal randomization works with different vibe modes"""
        effect = SaturationPulse(self.input_node)

        vibes = [
            Vibe(mode=Mode.rave),
            Vibe(mode=Mode.gentle),
            Vibe(mode=Mode.blackout),
        ]

        for vibe in vibes:
            with self.subTest(vibe_mode=vibe.mode):
                original_signal = effect.signal
                effect.generate(vibe)
                new_signal = effect.signal

                # Signal should be valid regardless of vibe mode
                self.assertIsInstance(new_signal, FrameSignal)

    def test_deterministic_signal_selection(self):
        """Test that we can control randomization for testing purposes"""
        effect = RGBShiftEffect(self.input_node)

        # Mock random.choice to return a specific signal
        with patch("parrot.vj.nodes.rgb_shift_effect.random.choice") as mock_choice:
            mock_choice.return_value = FrameSignal.strobe

            effect.generate(self.vibe)

            # Should have called random.choice with the available signals
            mock_choice.assert_called_once()
            args = mock_choice.call_args[0][0]  # Get the list passed to choice

            # Verify all expected signals are in the list
            expected_signals = [
                FrameSignal.freq_all,
                FrameSignal.freq_high,
                FrameSignal.freq_low,
                FrameSignal.sustained_low,
                FrameSignal.sustained_high,
                FrameSignal.strobe,
                FrameSignal.big_blinder,
                FrameSignal.small_blinder,
                FrameSignal.pulse,
                FrameSignal.dampen,
            ]
            self.assertEqual(set(args), set(expected_signals))

            # Effect should have the mocked signal
            self.assertEqual(effect.signal, FrameSignal.strobe)

    def test_effects_using_utility_function(self):
        """Test effects that use the utility function work correctly"""
        # BrightnessPulse uses the utility function
        effect = BrightnessPulse(self.input_node)

        with patch("parrot.vj.utils.signal_utils.random.choice") as mock_choice:
            mock_choice.return_value = FrameSignal.big_blinder

            effect.generate(self.vibe)

            self.assertEqual(effect.signal, FrameSignal.big_blinder)
            mock_choice.assert_called_once()

    def test_no_effects_without_generate_call(self):
        """Test that signals don't change without calling generate()"""
        effect = CameraZoom(self.input_node)
        original_signal = effect.signal

        # Create new instance - should have same default signal
        effect2 = CameraZoom(self.input_node)
        self.assertEqual(effect2.signal, original_signal)

        # Original effect signal should be unchanged
        self.assertEqual(effect.signal, original_signal)

    def test_all_frame_signals_available(self):
        """Test that all FrameSignal enum values are available for selection"""
        # Get all possible signals from the utility function
        with patch("parrot.vj.utils.signal_utils.random.choice") as mock_choice:
            # Mock choice to return a valid FrameSignal to satisfy beartype
            mock_choice.return_value = FrameSignal.freq_all

            get_random_frame_signal()

            available_signals = set(mock_choice.call_args[0][0])
            all_frame_signals = set(FrameSignal)

            self.assertEqual(
                available_signals,
                all_frame_signals,
                "All FrameSignal values should be available for selection",
            )

    def test_volumetric_beam_signal_randomization(self):
        """Test VolumetricBeam specifically (no input node required)"""
        beam = VolumetricBeam()
        original_signal = beam.signal

        # Generate multiple times to test randomization
        signals = set()
        for _ in range(10):
            beam.generate(self.vibe)
            signals.add(beam.signal)

        # Should be valid signals
        for signal in signals:
            self.assertIsInstance(signal, FrameSignal)

    def test_laser_array_signal_randomization(self):
        """Test LaserArray specifically (no input node required)"""
        import numpy as np

        # Create laser array with new interface
        camera_eye = np.array([0.0, 6.0, -8.0])
        camera_target = np.array([0.0, 6.0, 0.0])
        camera_up = np.array([0.0, 1.0, 0.0])
        laser_position = np.array([-4.0, 8.0, 2.0])
        laser_point_vector = camera_eye - laser_position
        laser_point_vector = laser_point_vector / np.linalg.norm(laser_point_vector)

        laser = LaserArray(
            camera_eye=camera_eye,
            camera_target=camera_target,
            camera_up=camera_up,
            laser_position=laser_position,
            laser_point_vector=laser_point_vector,
        )
        original_signal = laser.fan_signal  # New property name

        # Test randomization
        laser.generate(self.vibe)
        new_signal = laser.fan_signal  # New property name

        self.assertIsInstance(new_signal, FrameSignal)

    def test_oscilloscope_signal_randomization(self):
        """Test OscilloscopeEffect specifically (no input node required)"""
        osc = OscilloscopeEffect()
        original_signal = osc.signal

        # Test randomization
        osc.generate(self.vibe)
        new_signal = osc.signal

        self.assertIsInstance(new_signal, FrameSignal)


if __name__ == "__main__":
    unittest.main()
