import unittest
from unittest.mock import MagicMock
from parrot.director.frame import Frame, FrameSignal
from parrot.director.mode_interpretations import get_interpreter
from parrot.director.mode import Mode
from parrot.interpreters.base import InterpreterArgs
from parrot.fixtures.led_par import Par
from parrot.fixtures.motionstrip import Motionstrip
from parrot.director.color_scheme import ColorScheme
from parrot.utils.colour import Color
import random


class TestModes(unittest.TestCase):
    def setUp(self):
        # Create a test frame with some activity
        frame_values = {
            FrameSignal.freq_all: 0.8,  # High value to trigger beat detection
            FrameSignal.freq_high: 0.8,  # High value to trigger beat detection
            FrameSignal.freq_low: 0.8,  # High value to trigger beat detection
            FrameSignal.sustained_low: 0.1,
            FrameSignal.sustained_high: 0.8,  # High value to trigger effects
            FrameSignal.hype: 0.8,  # High value to trigger effects
        }
        timeseries = {
            FrameSignal.freq_all.name: [0.8] * 200,
            FrameSignal.freq_high.name: [0.8] * 200,
            FrameSignal.freq_low.name: [0.8] * 200,
            FrameSignal.sustained_low.name: [0.1] * 200,
            FrameSignal.sustained_high.name: [0.8] * 200,
            FrameSignal.hype.name: [0.8] * 200,
        }
        self.frame = Frame(frame_values, timeseries)
        self.args = InterpreterArgs(50, True, 0, 100)

        # Create a test color scheme
        self.scheme = ColorScheme(
            Color("red"), Color("blue"), Color("white")  # fg  # bg  # bg_contrast
        )

        # Create some mock fixtures
        self.par1 = MagicMock(spec=Par)
        self.par2 = MagicMock(spec=Par)
        self.par3 = MagicMock(spec=Par)
        self.pars = [self.par1, self.par2, self.par3]

        self.strip1 = MagicMock(spec=Motionstrip)
        self.strip2 = MagicMock(spec=Motionstrip)
        self.strips = [self.strip1, self.strip2]

        # Set initial dimmer values to 0
        for fixture in self.pars + self.strips:
            fixture.get_dimmer.return_value = 0.0

        # Ensure consistent random behavior
        random.seed(42)

    def test_party_mode_activates_lights(self):
        """Test that party mode activates at least some lights after one frame"""
        # Get party mode interpreter for pars
        interpreter = get_interpreter(Mode.party, self.pars, self.args)

        # Run multiple frames to ensure we get some activity
        for _ in range(5):  # Try a few frames
            interpreter.step(self.frame, self.scheme)

            # Check if any fixture has dimmer > 0
            dimmer_values = [
                fixture.set_dimmer.call_args[0][0]
                for fixture in self.pars
                if fixture.set_dimmer.called
            ]
            if any(value > 0 for value in dimmer_values):
                break
        else:
            self.fail("No lights were activated in party mode after multiple frames")

    def test_twinkle_mode_activates_lights(self):
        """Test that twinkle mode activates at least some lights after one frame"""
        # Get twinkle mode interpreter for strips (which use Twinkle interpreter)
        interpreter = get_interpreter(Mode.twinkle, self.strips, self.args)

        # Run one frame
        interpreter.step(self.frame, self.scheme)

        # Check that at least one fixture has dimmer > 0
        dimmer_values = [
            fixture.set_dimmer.call_args[0][0]
            for fixture in self.strips
            if fixture.set_dimmer.called
        ]
        self.assertTrue(
            any(value > 0 for value in dimmer_values),
            "No lights were activated in twinkle mode",
        )


if __name__ == "__main__":
    unittest.main()
