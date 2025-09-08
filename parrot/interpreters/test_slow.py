import pytest
from unittest.mock import MagicMock
from parrot.interpreters.slow import (
    SlowDecay,
    VerySlowDecay,
    SlowSustained,
    OnWhenNoSustained,
)
from parrot.interpreters.base import InterpreterArgs
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.fixtures.base import FixtureBase
from parrot.utils.colour import Color


class TestSlowDecay:
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

    def test_slow_decay_hype(self):
        """Test SlowDecay hype level"""
        assert SlowDecay.hype == 20

    def test_slow_decay_initialization(self):
        """Test SlowDecay initialization with custom parameters"""
        signal_fn = lambda x: x * 2
        interpreter = SlowDecay(
            self.group,
            self.args,
            decay_rate=0.2,
            signal=FrameSignal.freq_high,
            signal_fn=signal_fn,
        )

        assert interpreter.dimmer_memory == 0
        assert interpreter.decay_rate == 0.2
        assert interpreter.signal == FrameSignal.freq_high
        assert interpreter.signal_fn == signal_fn

    def test_slow_decay_step_with_signal(self):
        """Test SlowDecay step with signal input"""
        interpreter = SlowDecay(self.group, self.args, decay_rate=0.5)

        # Create frame with signal
        frame_values = {FrameSignal.freq_all: 0.8}
        timeseries = {signal.name: [0.0] * 100 for signal in FrameSignal}
        frame = Frame(frame_values, timeseries)

        interpreter.step(frame, self.scheme)

        # Should set dimmer to signal value (0.8 * 255)
        expected_dimmer = 0.8 * 255
        self.fixture1.set_dimmer.assert_called_with(expected_dimmer)
        self.fixture2.set_dimmer.assert_called_with(expected_dimmer)

        # Memory should be updated
        assert interpreter.dimmer_memory == 0.8

    def test_slow_decay_step_with_decay(self):
        """Test SlowDecay step with decay behavior"""
        interpreter = SlowDecay(self.group, self.args, decay_rate=0.3)
        interpreter.dimmer_memory = 1.0  # Set high initial memory

        # Create frame with low signal
        frame_values = {FrameSignal.freq_all: 0.2}
        timeseries = {signal.name: [0.0] * 100 for signal in FrameSignal}
        frame = Frame(frame_values, timeseries)

        interpreter.step(frame, self.scheme)

        # Memory should have decayed but taken max with signal
        # max(lerp(1.0, 0, 0.3), 0.2) = max(0.7, 0.2) = 0.7
        expected_memory = 0.7
        assert abs(interpreter.dimmer_memory - expected_memory) < 0.001

        expected_dimmer = expected_memory * 255
        self.fixture1.set_dimmer.assert_called_with(expected_dimmer)

    def test_slow_decay_step_no_signal(self):
        """Test SlowDecay step with no signal (pure decay)"""
        interpreter = SlowDecay(self.group, self.args, decay_rate=0.4)
        interpreter.dimmer_memory = 0.8  # Set initial memory

        # Create frame with no signal
        frame_values = {FrameSignal.freq_all: 0.0}
        timeseries = {signal.name: [0.0] * 100 for signal in FrameSignal}
        frame = Frame(frame_values, timeseries)

        interpreter.step(frame, self.scheme)

        # Should decay: lerp(0.8, 0, 0.4) = 0.8 * (1 - 0.4) = 0.48
        expected_memory = 0.48
        assert abs(interpreter.dimmer_memory - expected_memory) < 0.001

    def test_slow_decay_custom_signal_function(self):
        """Test SlowDecay with custom signal function"""
        signal_fn = lambda x: x**2  # Square the signal
        interpreter = SlowDecay(self.group, self.args, signal_fn=signal_fn)

        # Create frame with signal
        frame_values = {FrameSignal.freq_all: 0.5}
        timeseries = {signal.name: [0.0] * 100 for signal in FrameSignal}
        frame = Frame(frame_values, timeseries)

        interpreter.step(frame, self.scheme)

        # Signal function should be applied: 0.5^2 = 0.25
        expected_memory = 0.25
        assert abs(interpreter.dimmer_memory - expected_memory) < 0.001

    def test_slow_decay_custom_signal_type(self):
        """Test SlowDecay with custom signal type"""
        interpreter = SlowDecay(self.group, self.args, signal=FrameSignal.freq_low)

        # Create frame with freq_low signal
        frame_values = {FrameSignal.freq_low: 0.6, FrameSignal.freq_all: 0.1}
        timeseries = {signal.name: [0.0] * 100 for signal in FrameSignal}
        frame = Frame(frame_values, timeseries)

        interpreter.step(frame, self.scheme)

        # Should use freq_low signal, not freq_all
        expected_memory = 0.6
        assert abs(interpreter.dimmer_memory - expected_memory) < 0.001


class TestVerySlowDecay:
    def setup_method(self):
        """Setup for each test method"""
        self.fixture = MagicMock(spec=FixtureBase)
        self.group = [self.fixture]
        self.args = InterpreterArgs(
            hype=50, allow_rainbows=True, min_hype=0, max_hype=100
        )

    def test_very_slow_decay_properties(self):
        """Test VerySlowDecay has correct properties"""
        # This is created using with_args, so test the wrapper
        interpreter_class = VerySlowDecay
        interpreter = interpreter_class(self.group, self.args)

        # Should have modified hype and decay rate
        assert interpreter.get_hype() == 5
        assert interpreter.interpreter.decay_rate == 0.01

    def test_very_slow_decay_acceptable(self):
        """Test VerySlowDecay acceptable method"""
        # Should not allow rainbows
        args_with_rainbow = InterpreterArgs(
            hype=5, allow_rainbows=True, min_hype=0, max_hype=100
        )
        args_no_rainbow = InterpreterArgs(
            hype=5, allow_rainbows=False, min_hype=0, max_hype=100
        )

        # Both should be acceptable since the interpreter itself doesn't have rainbows
        assert VerySlowDecay.acceptable(args_with_rainbow) == True
        assert VerySlowDecay.acceptable(args_no_rainbow) == True


class TestSlowSustained:
    def setup_method(self):
        """Setup for each test method"""
        self.fixture = MagicMock(spec=FixtureBase)
        self.group = [self.fixture]
        self.args = InterpreterArgs(
            hype=50, allow_rainbows=True, min_hype=0, max_hype=100
        )

        # Create test scheme
        self.scheme = ColorScheme(
            fg=Color("red"), bg=Color("blue"), bg_contrast=Color("green")
        )

    def test_slow_sustained_properties(self):
        """Test SlowSustained has correct properties"""
        # This is created using with_args, so test the wrapper
        interpreter_class = SlowSustained
        interpreter = interpreter_class(self.group, self.args)

        # Should have modified hype, decay rate, and signal
        assert interpreter.get_hype() == 5
        assert interpreter.interpreter.decay_rate == 0.5
        assert interpreter.interpreter.signal == FrameSignal.sustained_low

    def test_slow_sustained_step(self):
        """Test SlowSustained responds to sustained_low signal"""
        interpreter = SlowSustained(self.group, self.args)

        # Create frame with sustained_low signal
        frame_values = {FrameSignal.sustained_low: 0.7}
        timeseries = {signal.name: [0.0] * 100 for signal in FrameSignal}
        frame = Frame(frame_values, timeseries)

        interpreter.step(frame, self.scheme)

        # Should respond to sustained_low signal
        expected_dimmer = 0.7 * 255
        self.fixture.set_dimmer.assert_called_with(expected_dimmer)


class TestOnWhenNoSustained:
    def setup_method(self):
        """Setup for each test method"""
        self.fixture = MagicMock(spec=FixtureBase)
        self.group = [self.fixture]
        self.args = InterpreterArgs(
            hype=50, allow_rainbows=True, min_hype=0, max_hype=100
        )

        # Create test scheme
        self.scheme = ColorScheme(
            fg=Color("red"), bg=Color("blue"), bg_contrast=Color("green")
        )

    def test_on_when_no_sustained_properties(self):
        """Test OnWhenNoSustained has correct properties"""
        # This is created using with_args, so test the wrapper
        interpreter_class = OnWhenNoSustained
        interpreter = interpreter_class(self.group, self.args)

        # Should have modified hype, decay rate, signal, and signal function
        assert interpreter.get_hype() == 0
        assert interpreter.interpreter.decay_rate == 0.01
        assert interpreter.interpreter.signal == FrameSignal.sustained_low

    def test_on_when_no_sustained_step_high_sustained(self):
        """Test OnWhenNoSustained with high sustained signal"""
        interpreter = OnWhenNoSustained(self.group, self.args)

        # Create frame with high sustained_low signal
        frame_values = {FrameSignal.sustained_low: 0.8}
        timeseries = {signal.name: [0.0] * 100 for signal in FrameSignal}
        frame = Frame(frame_values, timeseries)

        interpreter.step(frame, self.scheme)

        # Signal function is (1 - x), so 1 - 0.8 = 0.2
        expected_dimmer = 0.2 * 255
        actual_dimmer = self.fixture.set_dimmer.call_args[0][0]
        assert abs(actual_dimmer - expected_dimmer) < 0.01

    def test_on_when_no_sustained_step_low_sustained(self):
        """Test OnWhenNoSustained with low sustained signal"""
        interpreter = OnWhenNoSustained(self.group, self.args)

        # Create frame with low sustained_low signal
        frame_values = {FrameSignal.sustained_low: 0.2}
        timeseries = {signal.name: [0.0] * 100 for signal in FrameSignal}
        frame = Frame(frame_values, timeseries)

        interpreter.step(frame, self.scheme)

        # Signal function is (1 - x), so 1 - 0.2 = 0.8
        expected_dimmer = 0.8 * 255
        self.fixture.set_dimmer.assert_called_with(expected_dimmer)

    def test_on_when_no_sustained_step_no_sustained(self):
        """Test OnWhenNoSustained with no sustained signal"""
        interpreter = OnWhenNoSustained(self.group, self.args)

        # Create frame with no sustained_low signal
        frame_values = {FrameSignal.sustained_low: 0.0}
        timeseries = {signal.name: [0.0] * 100 for signal in FrameSignal}
        frame = Frame(frame_values, timeseries)

        interpreter.step(frame, self.scheme)

        # Signal function is (1 - x), so 1 - 0.0 = 1.0
        expected_dimmer = 1.0 * 255
        self.fixture.set_dimmer.assert_called_with(expected_dimmer)

    def test_on_when_no_sustained_acceptable(self):
        """Test OnWhenNoSustained acceptable method"""
        # Should accept any hype since it has hype=0
        args_low_hype = InterpreterArgs(
            hype=50, allow_rainbows=True, min_hype=10, max_hype=100
        )
        args_zero_hype = InterpreterArgs(
            hype=0, allow_rainbows=True, min_hype=0, max_hype=100
        )

        assert OnWhenNoSustained.acceptable(args_low_hype) == False  # 0 < 10
        assert OnWhenNoSustained.acceptable(args_zero_hype) == True  # 0 >= 0
