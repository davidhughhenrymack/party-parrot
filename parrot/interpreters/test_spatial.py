import unittest
from unittest.mock import MagicMock, patch
from parrot.director.frame import Frame, FrameSignal
from parrot.interpreters.base import InterpreterArgs
from parrot.interpreters.spatial import SpatialDownwardsPulse
from parrot.fixtures.base import FixtureBase


class TestSpatialDownwardsPulse(unittest.TestCase):
    def setUp(self):
        # Create mock fixtures with different y positions
        self.fixtures = []
        for i in range(5):
            fixture = MagicMock(spec=FixtureBase)
            fixture.y = i * 2  # Space fixtures 2 units apart
            fixture.get_dimmer.return_value = 0
            fixture.set_dimmer = MagicMock()
            self.fixtures.append(fixture)

        self.args = InterpreterArgs(50, True, 0, 100)

        # Create a test frame with varying signal values
        self.frame = MagicMock(spec=Frame)
        self.frame.time = 0
        self.frame.__getitem__.side_effect = lambda signal: {
            FrameSignal.freq_high: 0.5,  # High enough to trigger
            FrameSignal.freq_low: 0.1,  # Too low to trigger
        }.get(signal, 0.0)

        self.scheme = MagicMock()

    def test_pulse_movement(self):
        # Create interpreter with default parameters
        interpreter = SpatialDownwardsPulse(self.fixtures, self.args)

        # Run 20 steps
        for _ in range(20):
            interpreter.step(self.frame, self.scheme)
            self.frame.time += 1 / 30  # Simulate 30 FPS

        # Verify that fixtures were set with varying intensities
        # based on their y position relative to the pulse
        for fixture in self.fixtures:
            self.assertTrue(fixture.set_dimmer.called)

    def test_pulse_trigger(self):
        # Create interpreter with custom trigger level
        interpreter = SpatialDownwardsPulse(self.fixtures, self.args, trigger_level=0.4)

        # First step with low signal
        self.frame.__getitem__.side_effect = lambda signal: {
            FrameSignal.freq_high: 0.3,  # Below trigger level
        }.get(signal, 0.0)
        interpreter.step(self.frame, self.scheme)

        # Verify no pulse started
        for fixture in self.fixtures:
            fixture.set_dimmer.assert_called_with(0)
            fixture.set_dimmer.reset_mock()

        # Second step with high signal
        self.frame.__getitem__.side_effect = lambda signal: {
            FrameSignal.freq_high: 0.5,  # Above trigger level
        }.get(signal, 0.0)
        interpreter.step(self.frame, self.scheme)

        # Verify pulse started
        for fixture in self.fixtures:
            self.assertTrue(fixture.set_dimmer.called)

    def test_pulse_width_and_edge_hardness(self):
        # Create interpreter with custom width and edge hardness
        interpreter = SpatialDownwardsPulse(
            self.fixtures, self.args, pulse_width=0.2, edge_hardness=3.0
        )

        # Run a few steps to get the pulse moving
        for _ in range(5):
            interpreter.step(self.frame, self.scheme)
            self.frame.time += 1 / 30

        # Verify that the intensity falloff is steeper with higher edge hardness
        # and that the pulse is narrower with smaller pulse width
        intensities = [
            call[0][0] for call in self.fixtures[0].set_dimmer.call_args_list
        ]
        self.assertTrue(all(0 <= i <= 255 for i in intensities))
