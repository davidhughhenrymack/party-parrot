import unittest
from unittest.mock import MagicMock, patch
import time
from parrot.director.director import Director
from parrot.state import State
from parrot.director.frame import Frame, FrameSignal
from parrot.director.mode import Mode


class TestDirector(unittest.TestCase):
    def setUp(self):
        self.state = State()
        self.director = Director(self.state)

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


if __name__ == "__main__":
    unittest.main()
