import pytest
from unittest.mock import MagicMock, patch
from parrot.interpreters.latched import (
    DimmerBinaryLatched,
    DimmerFadeLatched,
    DimmerFadeLatched4s,
    DimmerFadeLatchedRandom,
)
from parrot.interpreters.base import InterpreterArgs
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.fixtures.base import FixtureBase
from parrot.utils.colour import Color


class TestDimmerBinaryLatched:
    def setup_method(self):
        """Setup for each test method"""
        self.fixture1 = MagicMock(spec=FixtureBase)
        self.fixture2 = MagicMock(spec=FixtureBase)
        self.group = [self.fixture1, self.fixture2]
        self.args = InterpreterArgs(
            hype=50, allow_rainbows=True, min_hype=0, max_hype=100
        )

        # Create test scheme
        self.scheme = ColorScheme(
            fg=Color("red"), bg=Color("blue"), bg_contrast=Color("green")
        )

    def test_dimmer_binary_latched_hype(self):
        """Test DimmerBinaryLatched hype level"""
        assert DimmerBinaryLatched.hype == 40

    def test_dimmer_binary_latched_initialization(self):
        """Test DimmerBinaryLatched initialization"""
        interpreter = DimmerBinaryLatched(
            self.group, self.args, signal=FrameSignal.freq_high
        )
        assert interpreter.signal == FrameSignal.freq_high
        assert interpreter.switch == False
        assert interpreter.latch_until == 0

    def test_dimmer_binary_latched_trigger_on(self):
        """Test DimmerBinaryLatched triggers on high signal"""
        interpreter = DimmerBinaryLatched(self.group, self.args)

        # Create frame with high sustained_low
        frame_values = {FrameSignal.sustained_low: 0.8}
        timeseries = {signal.name: [0.0] * 100 for signal in FrameSignal}
        frame = Frame(frame_values, timeseries)
        frame.time = 1.0

        interpreter.step(frame, self.scheme)

        # Should turn on
        assert interpreter.switch == True
        assert interpreter.latch_until > frame.time
        self.fixture1.set_dimmer.assert_called_with(255)
        self.fixture2.set_dimmer.assert_called_with(255)

    def test_dimmer_binary_latched_trigger_off(self):
        """Test DimmerBinaryLatched turns off on low signal"""
        interpreter = DimmerBinaryLatched(self.group, self.args)
        interpreter.switch = True  # Set initially on

        # Create frame with low sustained_low
        frame_values = {FrameSignal.sustained_low: 0.1}
        timeseries = {signal.name: [0.0] * 100 for signal in FrameSignal}
        frame = Frame(frame_values, timeseries)
        frame.time = 1.0

        interpreter.step(frame, self.scheme)

        # Should turn off
        assert interpreter.switch == False
        self.fixture1.set_dimmer.assert_called_with(0)
        self.fixture2.set_dimmer.assert_called_with(0)

    def test_dimmer_binary_latched_latch_duration(self):
        """Test DimmerBinaryLatched maintains latch for duration"""
        interpreter = DimmerBinaryLatched(self.group, self.args)

        # First frame: trigger on
        frame_values = {FrameSignal.sustained_low: 0.8}
        timeseries = {signal.name: [0.0] * 100 for signal in FrameSignal}
        frame = Frame(frame_values, timeseries)
        frame.time = 1.0
        interpreter.step(frame, self.scheme)

        # Second frame: signal goes low but still within latch time
        frame_values = {FrameSignal.sustained_low: 0.1}
        frame = Frame(frame_values, timeseries)
        frame.time = 1.2  # Still within 0.5s latch
        interpreter.step(frame, self.scheme)

        # Should still be on due to latch
        self.fixture1.set_dimmer.assert_called_with(255)


class TestDimmerFadeLatched:
    def setup_method(self):
        """Setup for each test method"""
        self.fixture = MagicMock(spec=FixtureBase)
        self.group = [self.fixture]
        self.args = InterpreterArgs(
            hype=50, allow_rainbows=True, min_hype=0, max_hype=100
        )

        self.scheme = ColorScheme(
            fg=Color("red"), bg=Color("blue"), bg_contrast=Color("green")
        )

    def test_dimmer_fade_latched_hype(self):
        """Test DimmerFadeLatched hype level"""
        assert DimmerFadeLatched.hype == 40

    def test_dimmer_fade_latched_initialization(self):
        """Test DimmerFadeLatched initialization with custom parameters"""
        condition_on = lambda x: x > 0.6
        condition_off = lambda x: x < 0.3

        interpreter = DimmerFadeLatched(
            self.group,
            self.args,
            signal=FrameSignal.freq_high,
            latch_time=1.0,
            condition_on=condition_on,
            condition_off=condition_off,
            fade_in_rate=0.2,
            fade_out_rate=0.15,
        )

        assert interpreter.signal == FrameSignal.freq_high
        assert interpreter.condition_on == condition_on
        assert interpreter.condition_off == condition_off
        assert interpreter.latch_time == 1.0
        assert interpreter.fade_in_rate == 0.2
        assert interpreter.fade_out_rate == 0.15
        assert interpreter.switch == False
        assert interpreter.latch_until == 0
        assert interpreter.memory == 0

    def test_dimmer_fade_latched_fade_in(self):
        """Test DimmerFadeLatched fades in when triggered"""
        interpreter = DimmerFadeLatched(self.group, self.args, fade_in_rate=0.5)

        # Create frame that triggers on condition
        frame_values = {FrameSignal.sustained_low: 0.8}
        timeseries = {signal.name: [0.0] * 100 for signal in FrameSignal}
        frame = Frame(frame_values, timeseries)
        frame.time = 1.0

        # Multiple steps to see fade progression
        initial_memory = interpreter.memory
        interpreter.step(frame, self.scheme)
        first_step_memory = interpreter.memory

        interpreter.step(frame, self.scheme)
        second_step_memory = interpreter.memory

        # Should fade in progressively
        assert first_step_memory > initial_memory
        assert second_step_memory > first_step_memory
        assert interpreter.switch == True

    def test_dimmer_fade_latched_fade_out(self):
        """Test DimmerFadeLatched fades out when signal drops"""
        interpreter = DimmerFadeLatched(self.group, self.args, fade_out_rate=0.3)
        interpreter.memory = 200  # Set high initial value
        interpreter.switch = False

        # Create frame with low signal
        frame_values = {FrameSignal.sustained_low: 0.1}
        timeseries = {signal.name: [0.0] * 100 for signal in FrameSignal}
        frame = Frame(frame_values, timeseries)
        frame.time = 1.0

        initial_memory = interpreter.memory
        interpreter.step(frame, self.scheme)

        # Should fade out
        assert interpreter.memory < initial_memory

    def test_dimmer_fade_latched_latch_behavior(self):
        """Test DimmerFadeLatched latch behavior"""
        interpreter = DimmerFadeLatched(self.group, self.args, latch_time=1.0)

        # First frame: trigger on
        frame_values = {FrameSignal.sustained_low: 0.8}
        timeseries = {signal.name: [0.0] * 100 for signal in FrameSignal}
        frame = Frame(frame_values, timeseries)
        frame.time = 1.0
        interpreter.step(frame, self.scheme)

        # Second frame: signal drops but within latch time
        frame_values = {FrameSignal.sustained_low: 0.1}
        frame = Frame(frame_values, timeseries)
        frame.time = 1.5  # Still within latch time
        interpreter.step(frame, self.scheme)

        # Should still be fading in due to latch
        assert interpreter.memory > 0

    def test_dimmer_fade_latched_custom_conditions(self):
        """Test DimmerFadeLatched with custom trigger conditions"""
        condition_on = lambda x: x > 0.7
        condition_off = lambda x: x < 0.2

        interpreter = DimmerFadeLatched(
            self.group,
            self.args,
            condition_on=condition_on,
            condition_off=condition_off,
        )

        # Test on condition
        frame_values = {FrameSignal.sustained_low: 0.8}
        timeseries = {signal.name: [0.0] * 100 for signal in FrameSignal}
        frame = Frame(frame_values, timeseries)
        frame.time = 1.0
        interpreter.step(frame, self.scheme)

        assert interpreter.switch == True

        # Test off condition
        frame_values = {FrameSignal.sustained_low: 0.15}
        frame = Frame(frame_values, timeseries)
        interpreter.step(frame, self.scheme)

        assert interpreter.switch == False


class TestDimmerFadeLatched4s:
    def setup_method(self):
        """Setup for each test method"""
        self.fixture = MagicMock(spec=FixtureBase)
        self.group = [self.fixture]
        self.args = InterpreterArgs(
            hype=50, allow_rainbows=True, min_hype=0, max_hype=100
        )

    def test_dimmer_fade_latched_4s_properties(self):
        """Test DimmerFadeLatched4s has correct properties"""
        # This is created using with_args, so test the wrapper
        interpreter_class = DimmerFadeLatched4s
        interpreter = interpreter_class(self.group, self.args)

        # Should have modified hype and rainbow properties
        assert interpreter.get_hype() == 10
        # Check that it's actually a DimmerFadeLatched with 4s latch time
        assert interpreter.interpreter.latch_time == 4

    def test_dimmer_fade_latched_4s_acceptable(self):
        """Test DimmerFadeLatched4s acceptable method"""
        # Should accept both rainbow and no-rainbow args since new_has_rainbow=False means it doesn't use rainbows
        args_with_rainbow = InterpreterArgs(
            hype=10, allow_rainbows=True, min_hype=0, max_hype=100
        )
        args_no_rainbow = InterpreterArgs(
            hype=10, allow_rainbows=False, min_hype=0, max_hype=100
        )

        # Both should be acceptable since the interpreter itself doesn't have rainbows
        assert DimmerFadeLatched4s.acceptable(args_with_rainbow) == True
        assert DimmerFadeLatched4s.acceptable(args_no_rainbow) == True

        # Test hype requirements - interpreter has hype=10, so max_hype=5 should make it unacceptable
        args_wrong_hype = InterpreterArgs(
            hype=50, allow_rainbows=True, min_hype=0, max_hype=5
        )
        assert DimmerFadeLatched4s.acceptable(args_wrong_hype) == False


class TestDimmerFadeLatchedRandom:
    def setup_method(self):
        """Setup for each test method"""
        self.fixture1 = MagicMock(spec=FixtureBase)
        self.fixture2 = MagicMock(spec=FixtureBase)
        self.fixture3 = MagicMock(spec=FixtureBase)
        self.group = [self.fixture1, self.fixture2, self.fixture3]
        self.args = InterpreterArgs(
            hype=50, allow_rainbows=True, min_hype=0, max_hype=100
        )

        self.scheme = ColorScheme(
            fg=Color("red"), bg=Color("blue"), bg_contrast=Color("green")
        )

    def test_dimmer_fade_latched_random_hype(self):
        """Test DimmerFadeLatchedRandom hype level"""
        assert DimmerFadeLatchedRandom.hype == 50

    def test_dimmer_fade_latched_random_initialization(self):
        """Test DimmerFadeLatchedRandom initialization"""
        interpreter = DimmerFadeLatchedRandom(
            self.group,
            self.args,
            signal=FrameSignal.freq_high,
            latch_at=0.6,
            latch_off_at=0.2,
            latch_time=1.0,
        )

        assert interpreter.signal == FrameSignal.freq_high
        assert interpreter.latch_at == 0.6
        assert interpreter.latch_off_at == 0.2
        assert interpreter.latch_time == 1.0
        assert interpreter.switch == False
        assert interpreter.selected is None
        assert interpreter.memory == 0

    @patch("random.choice")
    def test_dimmer_fade_latched_random_selection(self, mock_choice):
        """Test DimmerFadeLatchedRandom selects random fixture"""
        mock_choice.return_value = self.fixture2

        interpreter = DimmerFadeLatchedRandom(self.group, self.args)

        # Create frame that triggers latch
        frame_values = {FrameSignal.sustained_low: 0.8}
        timeseries = {signal.name: [0.0] * 100 for signal in FrameSignal}
        frame = Frame(frame_values, timeseries)
        frame.time = 1.0

        interpreter.step(frame, self.scheme)

        # Should have selected fixture2
        assert interpreter.selected == self.fixture2
        assert interpreter.switch == True
        mock_choice.assert_called_with(self.group)

    @patch("random.choice")
    def test_dimmer_fade_latched_random_fade_in(self, mock_choice):
        """Test DimmerFadeLatchedRandom fades in selected fixture"""
        mock_choice.return_value = self.fixture1

        interpreter = DimmerFadeLatchedRandom(self.group, self.args)

        # Create frame that triggers latch
        frame_values = {FrameSignal.sustained_low: 0.8}
        timeseries = {signal.name: [0.0] * 100 for signal in FrameSignal}
        frame = Frame(frame_values, timeseries)
        frame.time = 1.0

        # Multiple steps to see fade progression
        interpreter.step(frame, self.scheme)
        first_memory = interpreter.memory

        interpreter.step(frame, self.scheme)
        second_memory = interpreter.memory

        # Memory should increase
        assert second_memory > first_memory
        # Selected fixture should get the dimmer value
        self.fixture1.set_dimmer.assert_called_with(second_memory)

    @patch("random.choice")
    def test_dimmer_fade_latched_random_fade_out(self, mock_choice):
        """Test DimmerFadeLatchedRandom fades out when signal drops"""
        mock_choice.return_value = self.fixture1

        interpreter = DimmerFadeLatchedRandom(self.group, self.args)
        interpreter.selected = self.fixture1
        interpreter.memory = 200

        # Create frame with low signal
        frame_values = {FrameSignal.sustained_low: 0.05}
        timeseries = {signal.name: [0.0] * 100 for signal in FrameSignal}
        frame = Frame(frame_values, timeseries)
        frame.time = 1.0

        interpreter.step(frame, self.scheme)

        # Should turn off and clear selection
        assert interpreter.selected is None
        assert interpreter.memory == 0
        self.fixture1.set_dimmer.assert_called_with(0)

    @patch("random.choice")
    def test_dimmer_fade_latched_random_latch_behavior(self, mock_choice):
        """Test DimmerFadeLatchedRandom latch behavior"""
        mock_choice.return_value = self.fixture2

        interpreter = DimmerFadeLatchedRandom(self.group, self.args, latch_time=1.0)

        # First frame: trigger on
        frame_values = {FrameSignal.sustained_low: 0.8}
        timeseries = {signal.name: [0.0] * 100 for signal in FrameSignal}
        frame = Frame(frame_values, timeseries)
        frame.time = 1.0
        interpreter.step(frame, self.scheme)

        # Second frame: signal drops but within latch time
        frame_values = {
            FrameSignal.sustained_low: 0.3
        }  # Between latch_at and latch_off_at
        frame = Frame(frame_values, timeseries)
        frame.time = 1.5  # Still within latch time
        interpreter.step(frame, self.scheme)

        # Should still be active due to latch
        assert interpreter.selected == self.fixture2
        assert interpreter.memory > 0
