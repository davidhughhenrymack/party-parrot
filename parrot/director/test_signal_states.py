import unittest
import numpy as np
from parrot.director.signal_states import SignalStates
from parrot.director.frame import FrameSignal, Frame
from parrot.listeners.mic_to_dmx import MicToDmx
from parrot.state import State


class TestSignalStates(unittest.TestCase):
    def setUp(self):
        self.signal_states = SignalStates()
        self.state = State()

        # Create a mock args object with required attributes
        class MockArgs:
            def __init__(self):
                self.profile = False
                self.no_gui = True
                self.no_web = True
                self.web_port = 4040
                self.profile_interval = 30

        self.mic_to_dmx = MicToDmx(MockArgs())

    def test_initial_states(self):
        """Test that all signals start at 0.0"""
        states = self.signal_states.get_states()
        for signal in [
            FrameSignal.strobe,
            FrameSignal.big_pulse,
            FrameSignal.small_pulse,
            FrameSignal.twinkle,
        ]:
            self.assertEqual(states[signal], 0.0)

    def test_set_signal(self):
        """Test setting individual signal values"""
        self.signal_states.set_signal(FrameSignal.strobe, 1.0)
        states = self.signal_states.get_states()
        self.assertEqual(states[FrameSignal.strobe], 1.0)
        self.assertEqual(
            states[FrameSignal.big_pulse], 0.0
        )  # Others should remain unchanged

    def test_get_states_returns_copy(self):
        """Test that get_states returns a copy of the states"""
        states1 = self.signal_states.get_states()
        self.signal_states.set_signal(FrameSignal.strobe, 1.0)
        states2 = self.signal_states.get_states()
        self.assertNotEqual(states1[FrameSignal.strobe], states2[FrameSignal.strobe])

    def test_process_block_integration(self):
        """Test that signal states are properly integrated into frames"""
        # Create a mock spectrogram block with realistic frequency data
        # Initialize spectrogram with background noise
        mock_spectrogram = np.random.uniform(0.01, 0.05, (129, 100))

        # Add strong low frequency content (0-30 Hz range)
        mock_spectrogram[0:30, :] = np.random.uniform(0.8, 1.0, (30, 100))

        # Add some mid frequency content
        mock_spectrogram[30:60, :] = np.random.uniform(0.3, 0.5, (30, 100))

        # Add high frequency content (weaker)
        mock_spectrogram[60:, :] = np.random.uniform(0.1, 0.2, (69, 100))

        # Initialize signal stats buffer with some history
        # This helps normalize the frequency values
        for i in range(5):
            # Create variations of the mock spectrogram to build up history
            variation = mock_spectrogram.copy()
            # Add some random variation to the amplitudes
            variation *= np.random.uniform(0.8, 1.2)
            self.mic_to_dmx.process_block(variation, 100)

        # Set signal states on the MicToDmx instance's signal_states
        self.mic_to_dmx.signal_states.set_signal(FrameSignal.strobe, 1.0)
        self.mic_to_dmx.signal_states.set_signal(FrameSignal.big_pulse, 0.5)

        # Process the block one final time with the original spectrogram
        self.mic_to_dmx.process_block(mock_spectrogram, 100)

        # Get the frame from the last process_block call
        frame = self.mic_to_dmx.director.last_frame

        # Verify signal states were incorporated
        self.assertEqual(frame[FrameSignal.strobe], 1.0)
        self.assertEqual(frame[FrameSignal.big_pulse], 0.5)
        self.assertEqual(frame[FrameSignal.small_pulse], 0.0)  # Unchanged signal

        # Verify audio processing still works
        # After normalization, we expect both low and high frequencies to be between 0 and 1
        self.assertGreater(
            frame[FrameSignal.freq_low], 0.0
        )  # Should have some low frequency content
        self.assertLess(frame[FrameSignal.freq_low], 1.0)  # Should be normalized
        self.assertGreater(
            frame[FrameSignal.freq_high], 0.0
        )  # Should have some high frequency content
        self.assertLess(frame[FrameSignal.freq_high], 1.0)  # Should be normalized


if __name__ == "__main__":
    unittest.main()
