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
                self.no_web = True
                self.web_port = 4040
                self.profile_interval = 30

        self.mic_to_dmx = MicToDmx(MockArgs())

    def test_initial_states(self):
        """Test that all signals start at 0.0"""
        states = self.signal_states.get_states()
        for signal in [
            FrameSignal.strobe,
            FrameSignal.big_blinder,
            FrameSignal.small_blinder,
            FrameSignal.pulse,
        ]:
            self.assertEqual(states[signal], 0.0)

    def test_set_signal(self):
        """Test setting individual signal values"""
        self.signal_states.set_signal(FrameSignal.strobe, 1.0)
        states = self.signal_states.get_states()
        self.assertEqual(states[FrameSignal.strobe], 1.0)
        self.assertEqual(
            states[FrameSignal.big_blinder], 0.0
        )  # Others should remain unchanged

    def test_get_states_returns_copy(self):
        """Test that get_states returns a copy of the states"""
        states1 = self.signal_states.get_states()
        self.signal_states.set_signal(FrameSignal.strobe, 1.0)
        states2 = self.signal_states.get_states()
        self.assertNotEqual(states1[FrameSignal.strobe], states2[FrameSignal.strobe])


if __name__ == "__main__":
    unittest.main()
