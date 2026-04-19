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
        interpreter = MoveCircles(self.fixtures, self.args)

        assert interpreter.multiplier == 1
        # Deterministic per-fixture phase spread: i / N * 2π.
        # With 2 fixtures this gives [0, π] so the pair is half a revolution apart.
        assert interpreter._phase == [0.0, math.pi]

        interpreter.step(self.frame, self.scheme)
        self.fixture1.set_pan.assert_called_once()
        self.fixture1.set_tilt.assert_called_once()
        self.fixture2.set_pan.assert_called_once()
        self.fixture2.set_tilt.assert_called_once()

    def test_move_nod(self):
        """Test MoveNod interpreter"""
        interpreter = MoveNod(self.fixtures, self.args)

        assert interpreter.multiplier == 1
        # Deterministic per-fixture phase spread matches MoveCircles:
        # with 2 fixtures the pair is half a cycle apart so they nod in
        # opposition instead of in unison.
        assert interpreter._phase == [0.0, math.pi]

        interpreter.step(self.frame, self.scheme)
        self.fixture1.set_pan.assert_called_once_with(128)
        self.fixture1.set_tilt.assert_called_once()
        self.fixture2.set_pan.assert_called_once_with(128)
        self.fixture2.set_tilt.assert_called_once()

    def test_move_figure_eight(self):
        """Test MoveFigureEight interpreter"""
        interpreter = MoveFigureEight(self.fixtures, self.args)

        assert interpreter.multiplier == 1
        # Deterministic phase spread — no more random {0, π} choice.
        assert interpreter._phase == [0.0, math.pi]

        interpreter.step(self.frame, self.scheme)
        self.fixture1.set_pan.assert_called_once()
        self.fixture1.set_tilt.assert_called_once()
        self.fixture2.set_pan.assert_called_once()
        self.fixture2.set_tilt.assert_called_once()

    def test_move_fan(self):
        """Test MoveFan interpreter"""
        interpreter = MoveFan(self.fixtures, self.args)

        assert interpreter.multiplier == 1
        assert interpreter.spread == 1.0
        # Fan now also carries an even per-fixture phase on top of its
        # spatial amplitude envelope.
        assert interpreter._phase == [0.0, math.pi]

        interpreter.step(self.frame, self.scheme)
        self.fixture1.set_pan.assert_called_once()
        self.fixture1.set_tilt.assert_called_once_with(128)
        self.fixture2.set_pan.assert_called_once()
        self.fixture2.set_tilt.assert_called_once_with(128)

    def test_group_move_interpreters_spread_three_fixtures(self):
        """Every group-move interpreter evenly spaces phase as i / N * 2π."""
        fixture3 = MagicMock(spec=FixtureBase)
        fixtures = [self.fixture1, self.fixture2, fixture3]
        expected = [i / 3.0 * 2.0 * math.pi for i in range(3)]
        for cls in (MoveCircles, MoveNod, MoveFigureEight, MoveFan):
            interp = cls(fixtures, self.args)
            assert interp._phase == pytest.approx(expected), (
                f"{cls.__name__} did not produce even phase spread"
            )

    def test_move_circles_custom_multiplier(self):
        """Test MoveCircles with custom multiplier"""
        custom_multiplier = 0.18
        interpreter = MoveCircles(
            self.fixtures, self.args, multiplier=custom_multiplier
        )
        assert interpreter.multiplier == custom_multiplier

    def test_move_circles_phase_spread_three_fixtures(self):
        """Three fixtures should be evenly staggered at 0, 2π/3, 4π/3."""
        fixture3 = MagicMock(spec=FixtureBase)
        interpreter = MoveCircles(
            [self.fixture1, self.fixture2, fixture3], self.args
        )
        expected = [i / 3.0 * 2.0 * math.pi for i in range(3)]
        assert interpreter._phase == pytest.approx(expected)

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
