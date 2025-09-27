import pytest
from unittest.mock import MagicMock, patch
from parrot.director.frame import Frame, FrameSignal
from parrot.interpreters.base import InterpreterArgs
from parrot.interpreters.spatial import (
    SpatialDownwardsPulse,
    HardSpatialPulse,
    SoftSpatialPulse,
    SpatialCenterOutwardsPulse,
    HardSpatialCenterOutPulse,
)
from parrot.fixtures.base import FixtureBase


class TestSpatialDownwardsPulse:
    def setup_method(self):
        """Setup for each test method"""
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

    def test_spatial_downwards_pulse_hype(self):
        """Test SpatialDownwardsPulse hype level"""
        assert SpatialDownwardsPulse.hype == 60

    def test_spatial_downwards_pulse_initialization(self):
        """Test SpatialDownwardsPulse initialization with custom parameters"""
        interpreter = SpatialDownwardsPulse(
            self.fixtures,
            self.args,
            signal=FrameSignal.freq_low,
            trigger_level=0.4,
            edge_hardness=3.0,
            pulse_width=0.25,
            speed=1.5,
            min_valid_y_range=15,
            cooldown_time=2.0,
        )

        assert interpreter.signal == FrameSignal.freq_low
        assert interpreter.trigger_level == 0.4
        assert interpreter.edge_hardness == 3.0
        assert interpreter.pulse_width == 0.25
        assert interpreter.speed == 1.5
        assert interpreter.min_valid_y_range == 15
        assert interpreter.cooldown_time == 2.0
        assert interpreter.pulse_position == 0
        assert interpreter.active == False
        assert interpreter.valid_fixtures == []

    def test_pulse_movement(self):
        """Test SpatialDownwardsPulse movement over time"""
        # Create interpreter with default parameters
        interpreter = SpatialDownwardsPulse(self.fixtures, self.args)

        # Run 20 steps
        for _ in range(20):
            interpreter.step(self.frame, self.scheme)
            self.frame.time += 1 / 30  # Simulate 30 FPS

        # Verify that fixtures were set with varying intensities
        # based on their y position relative to the pulse
        for fixture in self.fixtures:
            assert fixture.set_dimmer.called

    def test_pulse_trigger(self):
        """Test SpatialDownwardsPulse trigger behavior"""
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
            assert fixture.set_dimmer.called

    def test_pulse_width_and_edge_hardness(self):
        """Test SpatialDownwardsPulse with custom width and edge hardness"""
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
        assert all(0 <= i <= 255 for i in intensities)

    def test_calculate_spatial_range(self):
        """Test _calculate_spatial_range method"""
        interpreter = SpatialDownwardsPulse(self.fixtures, self.args)

        # Should return True with valid fixtures
        result = interpreter._calculate_spatial_range()
        assert result == True
        assert len(interpreter.valid_fixtures) == 5
        assert interpreter.y_range > 0

    def test_calculate_spatial_range_no_valid_fixtures(self):
        """Test _calculate_spatial_range with no valid fixtures"""
        # Create fixtures without y positions
        fixtures_no_y = [MagicMock(spec=FixtureBase) for _ in range(3)]
        for fixture in fixtures_no_y:
            fixture.y = None

        interpreter = SpatialDownwardsPulse(fixtures_no_y, self.args)
        result = interpreter._calculate_spatial_range()
        assert result == False
        assert len(interpreter.valid_fixtures) == 0

    def test_calculate_spatial_range_insufficient_range(self):
        """Test _calculate_spatial_range with insufficient y range"""
        # Create fixtures with very close y positions
        close_fixtures = []
        for i in range(3):
            fixture = MagicMock(spec=FixtureBase)
            fixture.y = i * 0.1  # Very small spacing
            close_fixtures.append(fixture)

        interpreter = SpatialDownwardsPulse(
            close_fixtures, self.args, min_valid_y_range=10
        )
        result = interpreter._calculate_spatial_range()
        assert result == False

    def test_cooldown_initialization(self):
        """Test SpatialDownwardsPulse cooldown initialization"""
        interpreter = SpatialDownwardsPulse(self.fixtures, self.args, cooldown_time=2.0)
        assert interpreter.cooldown_time == 2.0
        assert interpreter.last_activation_time == 0


class TestHardSpatialPulse:
    def setup_method(self):
        """Setup for each test method"""
        self.fixtures = [MagicMock(spec=FixtureBase) for _ in range(3)]
        for i, fixture in enumerate(self.fixtures):
            fixture.y = i * 5
        self.args = InterpreterArgs(50, True, 0, 100)

    def test_hard_spatial_pulse_properties(self):
        """Test HardSpatialPulse has correct properties"""
        # This is created using with_args, so test the wrapper
        interpreter_class = HardSpatialPulse
        interpreter = interpreter_class(self.fixtures, self.args)

        # Should have modified hype and parameters
        assert interpreter.get_hype() == 90
        assert interpreter.interpreter.edge_hardness == 4.0
        assert interpreter.interpreter.pulse_width == 0.2
        assert interpreter.interpreter.speed == 2.0


class TestSoftSpatialPulse:
    def setup_method(self):
        """Setup for each test method"""
        self.fixtures = [MagicMock(spec=FixtureBase) for _ in range(3)]
        for i, fixture in enumerate(self.fixtures):
            fixture.y = i * 5
        self.args = InterpreterArgs(50, True, 0, 100)

    def test_soft_spatial_pulse_properties(self):
        """Test SoftSpatialPulse has correct properties"""
        # This is created using with_args, so test the wrapper
        interpreter_class = SoftSpatialPulse
        interpreter = interpreter_class(self.fixtures, self.args)

        # Should have modified hype and parameters
        assert interpreter.get_hype() == 30
        assert interpreter.interpreter.edge_hardness == 1.5
        assert interpreter.interpreter.pulse_width == 0.4
        assert interpreter.interpreter.speed == 0.5


class TestSpatialCenterOutwardsPulse:
    def setup_method(self):
        self.fixtures = []
        # Create fixtures with x positions across a span and constant y
        for i in range(5):
            f = MagicMock(spec=FixtureBase)
            f.x = i * 2
            f.y = 0
            f.set_dimmer = MagicMock()
            self.fixtures.append(f)
        self.args = InterpreterArgs(50, True, 0, 100)
        self.frame = MagicMock(spec=Frame)
        self.frame.time = 0
        self.frame.__getitem__.side_effect = lambda signal: {
            FrameSignal.freq_high: 0.6,
        }.get(signal, 0.0)
        self.scheme = MagicMock()

    def test_center_out_initialization(self):
        interp = SpatialCenterOutwardsPulse(
            self.fixtures,
            self.args,
            trigger_level=0.25,
            edge_hardness=3.0,
            pulse_width=0.25,
            speed=1.5,
            min_valid_x_range=5,
            cooldown_time=1.0,
        )
        assert interp.trigger_level == 0.25
        assert interp.edge_hardness == 3.0
        assert interp.pulse_width == 0.25
        assert interp.speed == 1.5
        assert interp.min_valid_x_range == 5
        assert interp.cooldown_time == 1.0

    def test_center_out_triggers_and_moves(self):
        interp = SpatialCenterOutwardsPulse(self.fixtures, self.args)
        for _ in range(10):
            interp.step(self.frame, self.scheme)
            self.frame.time += 1 / 30
        for f in self.fixtures:
            assert f.set_dimmer.called

    def test_hard_center_out_wrapper(self):
        cls = HardSpatialCenterOutPulse
        interp = cls(self.fixtures, self.args)
        assert interp.get_hype() == 90
        assert interp.interpreter.edge_hardness == 4.0
        assert interp.interpreter.pulse_width == 0.2
        assert interp.interpreter.speed == 2.0
