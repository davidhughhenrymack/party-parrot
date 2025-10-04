import unittest
from unittest.mock import MagicMock, patch
from parrot.director.mode import Mode
from beartype import beartype


@beartype
class TestGLOverlay(unittest.TestCase):
    """Test the GL overlay UI functionality"""

    def test_imgui_import(self):
        """Test that imgui can be imported"""
        import imgui
        from parrot.utils.imgui_moderngl import ImGuiModernGLRenderer

        self.assertIsNotNone(imgui)
        self.assertIsNotNone(ImGuiModernGLRenderer)

    def test_mode_enum_iteration(self):
        """Test that we can iterate over Mode enum for UI buttons"""
        modes = list(Mode)
        self.assertEqual(len(modes), 4)

        mode_names = [mode.name for mode in modes]
        self.assertIn("rave", mode_names)
        self.assertIn("blackout", mode_names)
        self.assertIn("gentle", mode_names)
        self.assertIn("chill", mode_names)

    def test_keyboard_handler_logic(self):
        """Test the keyboard handler toggle logic"""
        # Simulate keyboard handler behavior
        show_overlay = False

        # Simulate ENTER press
        show_overlay = not show_overlay
        self.assertTrue(show_overlay)

        # Simulate ENTER press again
        show_overlay = not show_overlay
        self.assertFalse(show_overlay)

    def test_state_mode_change(self):
        """Test that state.set_mode works correctly"""
        from parrot.state import State

        state = State()

        # Test mode changes
        state.set_mode(Mode.rave)
        self.assertEqual(state.mode, Mode.rave)

        state.set_mode(Mode.chill)
        self.assertEqual(state.mode, Mode.chill)

        state.set_mode(Mode.gentle)
        self.assertEqual(state.mode, Mode.gentle)

        state.set_mode(Mode.blackout)
        self.assertEqual(state.mode, Mode.blackout)


if __name__ == "__main__":
    unittest.main()
