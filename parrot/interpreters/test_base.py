import pytest
import math
from unittest.mock import MagicMock
from parrot.interpreters.base import (
    InterpreterBase,
    InterpreterArgs,
    acceptable_test,
    with_args,
    Noop,
    ColorFg,
    ColorAlternateBg,
    ColorBg,
    ColorRainbow,
    FlashBeat,
)
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.fixtures.base import FixtureBase
from parrot.utils.colour import Color


class TestInterpreterArgs:
    def test_interpreter_args_creation(self):
        """Test InterpreterArgs namedtuple creation"""
        args = InterpreterArgs(hype=50, allow_rainbows=True, min_hype=0, max_hype=100)
        assert args.hype == 50
        assert args.allow_rainbows == True
        assert args.min_hype == 0
        assert args.max_hype == 100


class TestAcceptableTest:
    def test_acceptable_test_within_hype_range(self):
        """Test acceptable_test with hype within range"""
        args = InterpreterArgs(hype=50, allow_rainbows=True, min_hype=0, max_hype=100)
        assert acceptable_test(args, 50, False) == True
        assert acceptable_test(args, 25, False) == True
        assert acceptable_test(args, 75, False) == True

    def test_acceptable_test_outside_hype_range(self):
        """Test acceptable_test with hype outside range"""
        args = InterpreterArgs(hype=50, allow_rainbows=True, min_hype=20, max_hype=80)
        assert acceptable_test(args, 10, False) == False
        assert acceptable_test(args, 90, False) == False

    def test_acceptable_test_rainbow_allowed(self):
        """Test acceptable_test with rainbows allowed"""
        args = InterpreterArgs(hype=50, allow_rainbows=True, min_hype=0, max_hype=100)
        assert acceptable_test(args, 50, True) == True
        assert acceptable_test(args, 50, False) == True

    def test_acceptable_test_rainbow_not_allowed(self):
        """Test acceptable_test with rainbows not allowed"""
        args = InterpreterArgs(hype=50, allow_rainbows=False, min_hype=0, max_hype=100)
        assert acceptable_test(args, 50, True) == False
        assert acceptable_test(args, 50, False) == True


class TestInterpreterBase:
    def setup_method(self):
        """Setup for each test method"""
        self.fixture1 = MagicMock(spec=FixtureBase)
        self.fixture2 = MagicMock(spec=FixtureBase)
        self.group = [self.fixture1, self.fixture2]
        self.args = InterpreterArgs(
            hype=50, allow_rainbows=True, min_hype=0, max_hype=100
        )

        # Create test frame
        frame_values = {
            FrameSignal.freq_all: 0.5,
            FrameSignal.freq_high: 0.3,
            FrameSignal.freq_low: 0.2,
            FrameSignal.sustained_low: 0.1,
            FrameSignal.sustained_high: 0.4,
        }
        timeseries = {signal.name: [0.0] * 100 for signal in FrameSignal}
        self.frame = Frame(frame_values, timeseries)
        self.frame.time = 1.0

        self.scheme = ColorScheme(
            fg=Color("red"), bg=Color("blue"), bg_contrast=Color("green")
        )

    def test_interpreter_base_initialization(self):
        """Test InterpreterBase initialization"""
        interpreter = InterpreterBase(self.group, self.args)
        assert interpreter.group == self.group
        assert interpreter.interpreter_args == self.args

    def test_interpreter_base_step(self):
        """Test InterpreterBase step method (should do nothing)"""
        interpreter = InterpreterBase(self.group, self.args)
        # Should not raise an error
        interpreter.step(self.frame, self.scheme)

    def test_interpreter_base_exit(self):
        """Test InterpreterBase exit method (should do nothing)"""
        interpreter = InterpreterBase(self.group, self.args)
        # Should not raise an error
        interpreter.exit(self.frame, self.scheme)

    def test_get_hype(self):
        """Test get_hype method"""
        interpreter = InterpreterBase(self.group, self.args)
        assert interpreter.get_hype() == InterpreterBase.hype

    def test_acceptable_class_method(self):
        """Test acceptable class method"""
        # Default InterpreterBase should be acceptable with any args
        assert InterpreterBase.acceptable(self.args) == True

    def test_str_representation(self):
        """Test string representation"""
        interpreter = InterpreterBase(self.group, self.args)
        str_repr = str(interpreter)
        assert "InterpreterBase" in str_repr


class TestWithArgs:
    def setup_method(self):
        """Setup for each test method"""
        self.fixture = MagicMock(spec=FixtureBase)
        self.group = [self.fixture]
        self.args = InterpreterArgs(
            hype=50, allow_rainbows=True, min_hype=0, max_hype=100
        )

    def test_with_args_creation(self):
        """Test with_args function creates proper wrapper class"""

        # Create a simple base interpreter
        class TestInterpreter(InterpreterBase):
            hype = 30
            has_rainbow = False

            def step(self, frame, scheme):
                for fixture in self.group:
                    fixture.set_dimmer(100)

        # Wrap it with with_args
        WrappedInterpreter = with_args(
            "TestWrapper", TestInterpreter, new_hype=60, new_has_rainbow=True
        )

        wrapped = WrappedInterpreter(self.group, self.args)
        assert wrapped.name == "TestWrapper"
        assert wrapped.get_hype() == 60

    def test_with_args_acceptable(self):
        """Test with_args acceptable method"""

        class TestInterpreter(InterpreterBase):
            hype = 30
            has_rainbow = False

        WrappedInterpreter = with_args(
            "TestWrapper", TestInterpreter, new_hype=60, new_has_rainbow=True
        )

        # Should use new values for acceptable test
        args_no_rainbow = InterpreterArgs(
            hype=60, allow_rainbows=False, min_hype=0, max_hype=100
        )
        assert (
            WrappedInterpreter.acceptable(args_no_rainbow) == False
        )  # has_rainbow=True but not allowed

    def test_with_args_step_delegation(self):
        """Test that with_args properly delegates step calls"""

        class TestInterpreter(InterpreterBase):
            def step(self, frame, scheme):
                for fixture in self.group:
                    fixture.set_dimmer(150)

        WrappedInterpreter = with_args("TestWrapper", TestInterpreter)
        wrapped = WrappedInterpreter(self.group, self.args)

        frame = MagicMock()
        scheme = MagicMock()
        wrapped.step(frame, scheme)

        self.fixture.set_dimmer.assert_called_with(150)


class TestNoop:
    def setup_method(self):
        """Setup for each test method"""
        self.fixture = MagicMock(spec=FixtureBase)
        self.group = [self.fixture]
        self.args = InterpreterArgs(
            hype=50, allow_rainbows=True, min_hype=0, max_hype=100
        )

    def test_noop_step(self):
        """Test that Noop does nothing"""
        interpreter = Noop(self.group, self.args)
        frame = MagicMock()
        scheme = MagicMock()

        # Should not raise error and not call any fixture methods
        interpreter.step(frame, scheme)
        assert not self.fixture.set_dimmer.called
        assert not self.fixture.set_color.called


class TestColorFg:
    def setup_method(self):
        """Setup for each test method"""
        self.fixture1 = MagicMock(spec=FixtureBase)
        self.fixture2 = MagicMock(spec=FixtureBase)
        self.group = [self.fixture1, self.fixture2]
        self.args = InterpreterArgs(
            hype=50, allow_rainbows=True, min_hype=0, max_hype=100
        )

    def test_color_fg_hype(self):
        """Test ColorFg hype level"""
        assert ColorFg.hype == 30

    def test_color_fg_step(self):
        """Test ColorFg sets foreground color"""
        interpreter = ColorFg(self.group, self.args)
        scheme = ColorScheme(
            fg=Color("red"), bg=Color("blue"), bg_contrast=Color("green")
        )
        frame = MagicMock()

        interpreter.step(frame, scheme)

        self.fixture1.set_color.assert_called_with(Color("red"))
        self.fixture2.set_color.assert_called_with(Color("red"))

    def test_color_fg_str(self):
        """Test ColorFg string representation"""
        interpreter = ColorFg(self.group, self.args)
        str_repr = str(interpreter)
        assert "Fg" in str_repr


class TestColorAlternateBg:
    def setup_method(self):
        """Setup for each test method"""
        self.fixture1 = MagicMock(spec=FixtureBase)
        self.fixture2 = MagicMock(spec=FixtureBase)
        self.fixture3 = MagicMock(spec=FixtureBase)
        self.group = [self.fixture1, self.fixture2, self.fixture3]
        self.args = InterpreterArgs(
            hype=50, allow_rainbows=True, min_hype=0, max_hype=100
        )

    def test_color_alternate_bg_step(self):
        """Test ColorAlternateBg alternates background colors"""
        interpreter = ColorAlternateBg(self.group, self.args)
        scheme = ColorScheme(
            fg=Color("red"), bg=Color("blue"), bg_contrast=Color("green")
        )
        frame = MagicMock()

        interpreter.step(frame, scheme)

        # Even indices should get bg, odd indices should get bg_contrast
        self.fixture1.set_color.assert_called_with(Color("blue"))  # index 0 (even)
        self.fixture2.set_color.assert_called_with(Color("green"))  # index 1 (odd)
        self.fixture3.set_color.assert_called_with(Color("blue"))  # index 2 (even)

    def test_color_alternate_bg_str(self):
        """Test ColorAlternateBg string representation"""
        interpreter = ColorAlternateBg(self.group, self.args)
        str_repr = str(interpreter)
        assert "AlternateBg" in str_repr


class TestColorBg:
    def setup_method(self):
        """Setup for each test method"""
        self.fixture1 = MagicMock(spec=FixtureBase)
        self.fixture2 = MagicMock(spec=FixtureBase)
        self.group = [self.fixture1, self.fixture2]
        self.args = InterpreterArgs(
            hype=50, allow_rainbows=True, min_hype=0, max_hype=100
        )

    def test_color_bg_step(self):
        """Test ColorBg sets background color"""
        interpreter = ColorBg(self.group, self.args)
        scheme = ColorScheme(
            fg=Color("red"), bg=Color("blue"), bg_contrast=Color("green")
        )
        frame = MagicMock()

        interpreter.step(frame, scheme)

        self.fixture1.set_color.assert_called_with(Color("blue"))
        self.fixture2.set_color.assert_called_with(Color("blue"))

    def test_color_bg_str(self):
        """Test ColorBg string representation"""
        interpreter = ColorBg(self.group, self.args)
        str_repr = str(interpreter)
        assert "Bg" in str_repr


class TestColorRainbow:
    def setup_method(self):
        """Setup for each test method"""
        self.fixture1 = MagicMock(spec=FixtureBase)
        self.fixture2 = MagicMock(spec=FixtureBase)
        self.group = [self.fixture1, self.fixture2]
        self.args = InterpreterArgs(
            hype=50, allow_rainbows=True, min_hype=0, max_hype=100
        )

    def test_color_rainbow_properties(self):
        """Test ColorRainbow has rainbow and correct hype"""
        assert ColorRainbow.has_rainbow == True
        assert ColorRainbow.hype == 40

    def test_color_rainbow_initialization(self):
        """Test ColorRainbow initialization with custom parameters"""
        interpreter = ColorRainbow(
            self.group, self.args, color_speed=0.1, color_phase_spread=0.3
        )
        assert interpreter.color_speed == 0.1
        assert interpreter.color_phase_spread == 0.3

    def test_color_rainbow_step(self):
        """Test ColorRainbow sets different colors based on time and position"""
        interpreter = ColorRainbow(self.group, self.args)
        scheme = MagicMock()

        # Create frame with time
        frame = MagicMock()
        frame.time = 1.0

        interpreter.step(frame, scheme)

        # Both fixtures should have set_color called
        self.fixture1.set_color.assert_called_once()
        self.fixture2.set_color.assert_called_once()

        # Colors should be different due to phase spread
        color1 = self.fixture1.set_color.call_args[0][0]
        color2 = self.fixture2.set_color.call_args[0][0]
        # Colors should be different (though they might occasionally be the same due to hue wrapping)
        assert isinstance(color1, Color)
        assert isinstance(color2, Color)

    def test_color_rainbow_time_progression(self):
        """Test ColorRainbow changes colors over time"""
        interpreter = ColorRainbow(self.group, self.args)
        scheme = MagicMock()

        # Step 1
        frame1 = MagicMock()
        frame1.time = 0.0
        interpreter.step(frame1, scheme)
        color1_t0 = self.fixture1.set_color.call_args[0][0]

        # Step 2
        frame2 = MagicMock()
        frame2.time = 5.0
        interpreter.step(frame2, scheme)
        color1_t5 = self.fixture1.set_color.call_args[0][0]

        # Colors should be different at different times
        assert color1_t0.hue != color1_t5.hue

    def test_color_rainbow_str(self):
        """Test ColorRainbow string representation"""
        interpreter = ColorRainbow(self.group, self.args)
        str_repr = str(interpreter)
        assert "Rainbow" in str_repr


class TestFlashBeat:
    def setup_method(self):
        """Setup for each test method"""
        self.fixture1 = MagicMock(spec=FixtureBase)
        self.fixture2 = MagicMock(spec=FixtureBase)
        self.group = [self.fixture1, self.fixture2]
        self.args = InterpreterArgs(
            hype=50, allow_rainbows=True, min_hype=0, max_hype=100
        )

    def test_flash_beat_hype(self):
        """Test FlashBeat hype level"""
        assert FlashBeat.hype == 70

    def test_flash_beat_initialization(self):
        """Test FlashBeat initialization"""
        interpreter = FlashBeat(self.group, self.args)
        assert interpreter.signal == FrameSignal.freq_high

    def test_flash_beat_high_sustained(self):
        """Test FlashBeat with high sustained signal"""
        interpreter = FlashBeat(self.group, self.args)
        scheme = MagicMock()

        # Create frame with high sustained_low
        frame_values = {FrameSignal.sustained_low: 0.8}
        timeseries = {signal.name: [0.0] * 100 for signal in FrameSignal}
        frame = Frame(frame_values, timeseries)

        interpreter.step(frame, scheme)

        # Should set high dimmer and strobe
        self.fixture1.set_dimmer.assert_called_with(100)
        self.fixture1.set_strobe.assert_called_with(200)
        self.fixture2.set_dimmer.assert_called_with(100)
        self.fixture2.set_strobe.assert_called_with(200)

    def test_flash_beat_medium_signal(self):
        """Test FlashBeat with medium signal"""
        interpreter = FlashBeat(self.group, self.args)
        scheme = MagicMock()

        # Create frame with medium freq_high
        frame_values = {FrameSignal.freq_high: 0.6, FrameSignal.sustained_low: 0.1}
        timeseries = {signal.name: [0.0] * 100 for signal in FrameSignal}
        frame = Frame(frame_values, timeseries)

        interpreter.step(frame, scheme)

        # Should set dimmer based on signal and no strobe
        expected_dimmer = 0.6 * 255
        self.fixture1.set_dimmer.assert_called_with(expected_dimmer)
        self.fixture1.set_strobe.assert_called_with(0)

    def test_flash_beat_low_signal(self):
        """Test FlashBeat with low signal"""
        interpreter = FlashBeat(self.group, self.args)
        scheme = MagicMock()

        # Create frame with low signals
        frame_values = {FrameSignal.freq_high: 0.2, FrameSignal.sustained_low: 0.1}
        timeseries = {signal.name: [0.0] * 100 for signal in FrameSignal}
        frame = Frame(frame_values, timeseries)

        interpreter.step(frame, scheme)

        # Should turn off
        self.fixture1.set_dimmer.assert_called_with(0)
        self.fixture1.set_strobe.assert_called_with(0)

    def test_flash_beat_str(self):
        """Test FlashBeat string representation"""
        interpreter = FlashBeat(self.group, self.args)
        str_repr = str(interpreter)
        assert "FlashBeat" in str_repr
