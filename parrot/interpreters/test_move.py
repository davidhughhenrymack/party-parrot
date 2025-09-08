import pytest
import math
from unittest.mock import MagicMock, patch
from parrot.interpreters.move import MoveCircles, MoveNod, MoveFigureEight, MoveFan
from parrot.interpreters.base import InterpreterArgs
from parrot.fixtures.base import FixtureBase


class TestMoveInterpreters:
    def setup_method(self):
        """Setup for each test method"""
        # Create mock fixtures
        self.fixture1 = MagicMock(spec=FixtureBase)
        self.fixture2 = MagicMock(spec=FixtureBase)
        self.fixtures = [self.fixture1, self.fixture2]

        # Create mock frame
        self.frame = MagicMock()
        self.frame.time = 0.0

        # Create mock scheme
        self.scheme = MagicMock()

        # Create interpreter args
        self.args = InterpreterArgs(
            hype=50, allow_rainbows=True, min_hype=0, max_hype=100
        )

    def test_move_circles(self):
        """Test MoveCircles interpreter"""
        # Test with default phase
        interpreter = MoveCircles(self.fixtures, self.args)

        # Test initial state
        assert interpreter.multiplier == 1
        assert interpreter.phase in [0, math.pi]

        # Test step with time = 0
        interpreter.step(self.frame, self.scheme)
        self.fixture1.set_pan.assert_called_once()
        self.fixture1.set_tilt.assert_called_once()
        self.fixture2.set_pan.assert_called_once()
        self.fixture2.set_tilt.assert_called_once()

    def test_move_nod(self):
        """Test MoveNod interpreter"""
        interpreter = MoveNod(self.fixtures, self.args)

        # Test initial state
        assert interpreter.multiplier == 1
        assert interpreter.phase == math.pi / 3

        # Test step with time = 0
        interpreter.step(self.frame, self.scheme)
        self.fixture1.set_pan.assert_called_once_with(128)
        self.fixture1.set_tilt.assert_called_once()
        self.fixture2.set_pan.assert_called_once_with(128)
        self.fixture2.set_tilt.assert_called_once()

    def test_move_figure_eight(self):
        """Test MoveFigureEight interpreter"""
        interpreter = MoveFigureEight(self.fixtures, self.args)

        # Test initial state
        assert interpreter.multiplier == 1
        assert interpreter.phase in [0, math.pi]

        # Test step with time = 0
        interpreter.step(self.frame, self.scheme)
        self.fixture1.set_pan.assert_called_once()
        self.fixture1.set_tilt.assert_called_once()
        self.fixture2.set_pan.assert_called_once()
        self.fixture2.set_tilt.assert_called_once()

    def test_move_fan(self):
        """Test MoveFan interpreter"""
        interpreter = MoveFan(self.fixtures, self.args)

        # Test initial state
        assert interpreter.multiplier == 1
        assert interpreter.spread == 1.0

        # Test step with time = 0
        interpreter.step(self.frame, self.scheme)
        self.fixture1.set_pan.assert_called_once()
        self.fixture1.set_tilt.assert_called_once_with(128)
        self.fixture2.set_pan.assert_called_once()
        self.fixture2.set_tilt.assert_called_once_with(128)

    def test_move_circles_custom_phase(self):
        """Test MoveCircles with custom phase"""
        custom_phase = math.pi / 2
        interpreter = MoveCircles(self.fixtures, self.args, phase=custom_phase)
        assert interpreter.phase == custom_phase

    def test_move_nod_custom_multiplier(self):
        """Test MoveNod with custom multiplier"""
        custom_multiplier = 2.0
        interpreter = MoveNod(self.fixtures, self.args, multiplier=custom_multiplier)
        assert interpreter.multiplier == custom_multiplier

    def test_move_figure_eight_custom_multiplier(self):
        """Test MoveFigureEight with custom multiplier"""
        custom_multiplier = 2.0
        interpreter = MoveFigureEight(
            self.fixtures, self.args, multiplier=custom_multiplier
        )
        assert interpreter.multiplier == custom_multiplier

    def test_move_fan_custom_spread(self):
        """Test MoveFan with custom spread"""
        custom_spread = 0.5
        interpreter = MoveFan(self.fixtures, self.args, spread=custom_spread)
        assert interpreter.spread == custom_spread

    def test_move_fan_odd_number_fixtures(self):
        """Test MoveFan with odd number of fixtures"""
        # Test with 3 fixtures to ensure middle fixture behavior
        fixture3 = MagicMock(spec=FixtureBase)
        fixtures = [self.fixture1, self.fixture2, fixture3]

        interpreter = MoveFan(fixtures, self.args)
        interpreter.step(self.frame, self.scheme)

        # Middle fixture (fixture2) should have pan = 128
        self.fixture2.set_pan.assert_called_once_with(128)
        self.fixture2.set_tilt.assert_called_once_with(128)

    def test_move_circles_str(self):
        """Test MoveCircles string representation"""
        interpreter = MoveCircles(self.fixtures, self.args)
        str_repr = str(interpreter)
        assert "Circles" in str_repr

    def test_move_nod_str(self):
        """Test MoveNod string representation"""
        interpreter = MoveNod(self.fixtures, self.args)
        str_repr = str(interpreter)
        assert "Nod" in str_repr

    def test_move_figure_eight_str(self):
        """Test MoveFigureEight string representation"""
        interpreter = MoveFigureEight(self.fixtures, self.args)
        str_repr = str(interpreter)
        assert "FigureEight" in str_repr

    def test_move_fan_str(self):
        """Test MoveFan string representation"""
        interpreter = MoveFan(self.fixtures, self.args)
        str_repr = str(interpreter)
        assert "Fan" in str_repr
