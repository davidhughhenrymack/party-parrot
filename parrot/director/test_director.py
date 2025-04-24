import unittest
from unittest.mock import MagicMock, patch
import time
import numpy as np
from parrot.director.director import Director
from parrot.state import State
from parrot.director.frame import Frame, FrameSignal
from parrot.director.mode import Mode
from parrot.fixtures.base import FixtureBase
from parrot.interpreters.base import InterpreterArgs


class TestDirector(unittest.TestCase):
    def setUp(self):
        self.state = State()
        self.director = Director(self.state)
        self.dmx = MagicMock()
        self.fixture = FixtureBase(1, "Test Fixture", 1)
        self.fixture.values = [255]  # Set to full brightness

    def test_initialization(self):
        """Test that the director initializes correctly"""
        self.assertIsNotNone(self.director.scheme)
        self.assertIsNotNone(self.director.mode_machine)
        self.assertEqual(self.director.state, self.state)
        self.assertFalse(self.director.warmup_complete)

    def test_setup_patch(self):
        """Test that setup_patch creates fixture groups and interpreters"""
        self.director.setup_patch()
        self.assertIsNotNone(self.director.fixture_groups)
        self.assertIsNotNone(self.director.interpreters)

    def test_mode_change(self):
        """Test that mode changes trigger interpreter regeneration"""
        with patch.object(self.director, "generate_interpreters") as mock_gen:
            self.director.on_mode_change(Mode.party)
            mock_gen.assert_called_once()

    def test_shift_color_scheme(self):
        """Test that color scheme shifting works"""
        original_scheme = self.director.scheme.render()
        self.director.shift_color_scheme()
        new_scheme = self.director.scheme.render()
        self.assertNotEqual(original_scheme, new_scheme)

    def test_set_scene_value(self):
        """Test setting scene values."""
        self.director.set_scene_value("manual_fixtures", 0.5)
        self.assertEqual(self.director.scene_values["manual_fixtures"], 0.5)

        # Setting a new value should update the existing one
        self.director.set_scene_value("manual_fixtures", 0.75)
        self.assertEqual(self.director.scene_values["manual_fixtures"], 0.75)

    def test_generate_interpreters(self):
        """Test generating interpreters for modes and scenes."""
        # Set up a scene value
        self.director.set_scene_value("manual_fixtures", 0.5)

        # Generate interpreters
        self.director.generate_interpreters()

        # Check that interpreters were generated
        self.assertGreater(len(self.director.interpreters), 0)

    @patch("parrot.director.director.get_interpreter")
    @patch("parrot.director.director.get_scene_interpreter")
    def test_render(self, mock_get_scene_interpreter, mock_get_interpreter):
        """Test rendering with scene values."""
        # Set up mock interpreters
        mode_interpreter = MagicMock()
        mode_interpreter.group = [self.fixture]
        mode_interpreter.step.return_value = None
        mock_get_interpreter.return_value = mode_interpreter

        scene_interpreter = MagicMock()
        scene_interpreter.group = [self.fixture]
        scene_interpreter.step.return_value = None
        mock_get_scene_interpreter.return_value = scene_interpreter

        # Set up scene value
        self.director.set_scene_value("manual_fixtures", 0.5)

        # Generate interpreters
        self.director.generate_interpreters()

        # Render
        self.director.render(self.dmx)

        # Check that DMX values were set correctly
        # Mode should be at full strength (1.0)
        # Scene should be at 0.5 strength
        # Highest value should be used
        self.dmx.set_channel.assert_called_with(1, 255)  # Full brightness from mode

    def test_highest_takes_precedence(self):
        """Test that highest value takes precedence."""
        # Create two fixtures with different values
        fixture1 = FixtureBase(1, "Fixture 1", 1)
        fixture1.values = [100]  # Lower value

        fixture2 = FixtureBase(1, "Fixture 2", 1)
        fixture2.values = [200]  # Higher value

        # Set up interpreters
        self.director.interpreters = {
            (Mode.party, 1): MagicMock(group=[fixture1]),
            ("manual_fixtures", 1): MagicMock(group=[fixture2]),
        }

        # Set scene value
        self.director.scene_values = {"manual_fixtures": 1.0}

        # Render
        self.director.render(self.dmx)

        # Check that the higher value was used
        self.dmx.set_channel.assert_called_with(1, 200)


if __name__ == "__main__":
    unittest.main()
