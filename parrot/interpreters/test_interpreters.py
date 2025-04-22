import unittest
from unittest.mock import MagicMock, patch
from parrot.director.frame import Frame, FrameSignal
from parrot.interpreters.base import (
    InterpreterBase,
    InterpreterArgs,
    ColorBg,
    ColorFg,
    ColorRainbow,
)
from parrot.interpreters.dimmer import (
    Dimmer255,
    DimmerFadeIn,
    DimmersBeatChase,
    GentlePulse,
)
from parrot.interpreters.combo import combo
from parrot.utils.colour import Color
from parrot.director.color_scheme import ColorScheme
import random


class TestInterpreters(unittest.TestCase):
    def setUp(self):
        self.fixture = MagicMock()
        self.fixture.get_dimmer.return_value = 0.0
        self.fixture.get_color.return_value = Color("black")
        self.args = InterpreterArgs(50, True, 0, 100)

        # Create a test frame
        frame_values = {
            FrameSignal.freq_all: 0.5,
            FrameSignal.freq_high: 0.3,
            FrameSignal.freq_low: 0.2,
            FrameSignal.sustained_low: 0.1,
            FrameSignal.sustained_high: 0.4,
            FrameSignal.hype: 0.6,
        }
        timeseries = {
            FrameSignal.freq_all.name: [0.5] * 200,
            FrameSignal.freq_high.name: [0.3] * 200,
            FrameSignal.freq_low.name: [0.2] * 200,
            FrameSignal.sustained_low.name: [0.1] * 200,
            FrameSignal.sustained_high.name: [0.4] * 200,
            FrameSignal.hype.name: [0.6] * 200,
        }
        self.frame = Frame(frame_values, timeseries)

    def test_dimmer255(self):
        """Test that Dimmer255 sets fixture to full brightness"""
        interpreter = Dimmer255([self.fixture], self.args)
        interpreter.step(self.frame, Color("white"))
        self.fixture.set_dimmer.assert_called_once_with(255)

    def test_dimmer_fade_in(self):
        """Test that DimmerFadeIn gradually increases brightness"""
        interpreter = DimmerFadeIn([self.fixture], self.args)

        # First step should start fade
        self.frame.time = 0
        interpreter.step(self.frame, Color("white"))
        initial_value = self.fixture.set_dimmer.call_args[0][0]
        self.assertGreater(initial_value, 0)

        # Simulate time passing
        self.frame.time = 1 / 30  # One frame at 30fps
        interpreter.step(self.frame, Color("white"))
        self.assertGreater(self.fixture.set_dimmer.call_args[0][0], initial_value)

    def test_dimmers_beat_chase(self):
        """Test that DimmersBeatChase responds to beats"""
        interpreter = DimmersBeatChase([self.fixture], self.args)
        self.frame.values[FrameSignal.freq_all] = 0.8  # Simulate beat
        interpreter.step(self.frame, Color("white"))
        # The fixture should be set to 0 initially since it's not the selected bulb
        self.fixture.set_dimmer.assert_called_with(0)

    def test_gentle_pulse(self):
        """Test that GentlePulse creates smooth brightness changes"""
        interpreter = GentlePulse([self.fixture], self.args)

        # Force random selection to always pick our fixture
        random.seed(42)  # Ensure consistent random behavior

        # First step: trigger the pulse
        self.frame.time = 0
        self.frame.values[FrameSignal.freq_all] = 0.8  # Well above trigger level
        interpreter.step(self.frame, Color("white"))
        initial_value = self.fixture.set_dimmer.call_args[0][0]

        # Second step: let it decay
        self.frame.time = 1 / 30
        self.frame.values[FrameSignal.freq_all] = 0.1  # Below trigger level
        interpreter.step(self.frame, Color("white"))
        decayed_value = self.fixture.set_dimmer.call_args[0][0]

        # Values should be different due to decay
        self.assertNotEqual(initial_value, decayed_value)
        self.assertLess(decayed_value, initial_value)  # Decayed value should be less

    def test_color_bg(self):
        """Test that ColorBg sets background colors"""
        interpreter = ColorBg([self.fixture], self.args)
        test_color = Color("blue")
        scheme = ColorScheme(Color("black"), test_color, Color("white"))
        interpreter.step(self.frame, scheme)
        self.fixture.set_color.assert_called_with(test_color)

    def test_color_fg(self):
        """Test that ColorFg sets foreground colors"""
        interpreter = ColorFg([self.fixture], self.args)
        test_color = Color("red")
        scheme = ColorScheme(test_color, Color("black"), Color("white"))
        interpreter.step(self.frame, scheme)
        self.fixture.set_color.assert_called_with(test_color)

    def test_color_rainbow(self):
        """Test that ColorRainbow cycles through colors"""
        interpreter = ColorRainbow([self.fixture], self.args)

        # Multiple steps should show different colors
        colors = set()
        for i in range(10):  # Increased steps to ensure color variation
            self.frame.time = i / 30  # Simulate time passing at 30fps
            interpreter.step(self.frame, Color("white"))
            colors.add(str(self.fixture.set_color.call_args[0][0]))

        # Should have multiple different colors
        self.assertGreater(len(colors), 1)

    def test_combo_interpreter(self):
        """Test that combo interpreter combines multiple effects"""
        interpreter = combo(Dimmer255, ColorBg)([self.fixture], self.args)
        test_color = Color("green")
        scheme = ColorScheme(Color("black"), test_color, Color("white"))
        interpreter.step(self.frame, scheme)

        self.fixture.set_dimmer.assert_called_with(255)
        self.fixture.set_color.assert_called_with(test_color)


if __name__ == "__main__":
    unittest.main()
