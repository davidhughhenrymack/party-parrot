#!/usr/bin/env python3

import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from beartype import beartype

from parrot.audio.audio_analyzer import AudioAnalyzer
from parrot.director.signal_states import SignalStates
from parrot.director.frame import Frame, FrameSignal


class TestAudioAnalyzer:
    """Test the AudioAnalyzer class"""

    @pytest.fixture
    def mock_pyaudio(self):
        """Mock PyAudio to avoid needing real audio hardware"""
        with patch("parrot.audio.audio_analyzer.pyaudio.PyAudio") as mock_pa:
            mock_stream = Mock()
            mock_stream.get_read_available.return_value = 1024
            mock_stream.read.return_value = np.random.randint(
                -32768, 32767, 1024, dtype=np.int16
            ).tobytes()

            mock_pa_instance = Mock()
            mock_pa_instance.open.return_value = mock_stream
            mock_pa_instance.get_device_count.return_value = 1
            mock_pa_instance.get_device_info_by_index.return_value = {
                "name": "Test Microphone"
            }

            mock_pa.return_value = mock_pa_instance
            yield mock_pa_instance

    def test_initialization(self, mock_pyaudio):
        """Test that AudioAnalyzer initializes correctly"""
        signal_states = SignalStates()
        analyzer = AudioAnalyzer(signal_states)

        assert analyzer.signal_states == signal_states
        assert analyzer.spectrogram_buffer is None
        assert len(analyzer.signal_lookback) == 2

    def test_process_spectrogram(self, mock_pyaudio):
        """Test that spectrogram processing produces a valid Frame"""
        analyzer = AudioAnalyzer()

        # Create a test spectrogram (frequency bins x time steps)
        test_spectrogram = np.random.rand(129, 100)

        frame = analyzer.process_spectrogram(test_spectrogram, num_idx_added=10)

        # Check that frame has expected signal values
        assert isinstance(frame, Frame)
        assert FrameSignal.freq_low in frame.values
        assert FrameSignal.freq_high in frame.values
        assert FrameSignal.sustained_low in frame.values
        assert FrameSignal.sustained_high in frame.values

        # Check that values are in 0-1 range
        for key, value in frame.values.items():
            if isinstance(key, FrameSignal):
                assert 0 <= value <= 1, f"{key} value {value} is out of range"

    def test_read_audio_block(self, mock_pyaudio):
        """Test reading an audio block"""
        analyzer = AudioAnalyzer()

        # Mock the stream to return audio data
        # Use a callable mock that alternates between 0 and 1024 to simulate waiting
        call_count = [0]

        def get_read_available_mock():
            call_count[0] += 1
            # Return 1024 on most calls, 0 occasionally to simulate waiting
            return 1024 if call_count[0] % 3 != 1 else 0

        mock_stream = analyzer.stream
        mock_stream.get_read_available = get_read_available_mock
        mock_stream.read.return_value = np.random.randint(
            -32768, 32767, 1024, dtype=np.int16
        ).tobytes()

        audio_block = analyzer.read_audio_block()

        assert isinstance(audio_block, np.ndarray)
        assert len(audio_block) > 0

    def test_cleanup(self, mock_pyaudio):
        """Test cleanup releases resources"""
        analyzer = AudioAnalyzer()
        analyzer.cleanup()

        # Verify stream was closed
        analyzer.stream.stop_stream.assert_called_once()
        analyzer.stream.close.assert_called_once()
        analyzer.pa.terminate.assert_called_once()
