import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from parrot.listeners.mic_to_dmx import get_rms, MicToDmx


class TestMicToDmx:
    def test_get_rms_zero_block(self):
        """Test get_rms with zero block."""
        block = np.zeros(1024)
        rms = get_rms(block)
        assert rms == 0.0

    def test_get_rms_constant_block(self):
        """Test get_rms with constant value block."""
        block = np.full(1024, 0.5)
        rms = get_rms(block)
        assert rms == 0.5

    def test_get_rms_sine_wave(self):
        """Test get_rms with sine wave."""
        # Create a sine wave
        t = np.linspace(0, 1, 1024)
        block = np.sin(2 * np.pi * 440 * t)  # 440 Hz sine wave
        rms = get_rms(block)
        # RMS of sine wave should be approximately 1/sqrt(2) ≈ 0.707
        assert abs(rms - (1 / np.sqrt(2))) < 0.01

    def test_get_rms_empty_block(self):
        """Test get_rms with empty block."""
        block = np.array([])
        rms = get_rms(block)
        assert np.isnan(rms)
