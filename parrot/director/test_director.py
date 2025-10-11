import unittest
from unittest.mock import MagicMock, patch
import time
import tempfile
import shutil
import os
from parrot.director.director import Director
from parrot.state import State
from parrot.director.frame import Frame, FrameSignal
from parrot.director.mode import Mode


class TestDirector(unittest.TestCase):
    def setUp(self):
        # Create a temporary directory for test isolation
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)

        self.state = State()
        self.director = Director(self.state)

    def tearDown(self):
        """Clean up after each test method."""
        # Change back to original directory first
        os.chdir(self.original_cwd)
        # Clean up entire temp directory and all its contents
        if os.path.exists(self.temp_dir):
            shutil.rmtree(self.temp_dir)

    def test_isolation_from_real_state_file(self):
        """Test that tests run in isolated temp directory, not touching real state.json"""
        # Verify we're in a temp directory (use realpath to resolve symlinks on macOS)
        current_dir = os.path.realpath(os.getcwd())
        temp_dir = os.path.realpath(self.temp_dir)
        self.assertEqual(current_dir, temp_dir)
        self.assertTrue("/tmp" in current_dir or "/var/folders" in current_dir)

        # Verify we're NOT in the project directory
        self.assertNotEqual(current_dir, os.path.realpath(self.original_cwd))

    def test_initialization(self):
        """Test that the director initializes correctly"""
        self.assertIsNotNone(self.director.scheme)
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
            self.director.on_mode_change(Mode.rave)
            mock_gen.assert_called_once()

    def test_shift_color_scheme(self):
        """Test that color scheme shifting works"""
        original_scheme = self.director.scheme.render()
        self.director.shift_color_scheme()
        new_scheme = self.director.scheme.render()
        self.assertNotEqual(original_scheme, new_scheme)


if __name__ == "__main__":
    unittest.main()
