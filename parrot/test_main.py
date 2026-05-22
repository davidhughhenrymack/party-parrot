import unittest
from unittest.mock import patch, MagicMock
import argparse
from parrot.main import parse_arguments, run
from parrot.listeners.mic_to_dmx import MicToDmx


class TestMain(unittest.TestCase):
    def test_parse_arguments_default(self):
        """Test that argument parsing works with default values"""
        with patch("sys.argv", ["main.py"]):
            args = parse_arguments()
            self.assertFalse(args.profile)
            self.assertEqual(args.profile_interval, 10)
            self.assertFalse(args.plot)
            self.assertEqual(args.web_port, 4040)
            self.assertFalse(args.no_web)
            self.assertFalse(args.screenshot)
            self.assertFalse(args.start_with_overlay)
            self.assertFalse(args.windowed)

    def test_parse_arguments_custom(self):
        """Test that argument parsing works with custom values"""
        test_args = [
            "main.py",
            "--profile",
            "--profile-interval",
            "20",
            "--plot",
            "--web-port",
            "8080",
            "--no-web",
        ]
        with patch("sys.argv", test_args):
            args = parse_arguments()
            self.assertTrue(args.profile)
            self.assertEqual(args.profile_interval, 20)
            self.assertTrue(args.plot)
            self.assertEqual(args.web_port, 8080)
            self.assertTrue(args.no_web)

    def test_parse_arguments_windowed(self):
        with patch("sys.argv", ["main.py", "--windowed"]):
            args = parse_arguments()
            self.assertTrue(args.windowed)

    def test_run_defaults_to_headless_bridge(self):
        args = argparse.Namespace(
            windowed=False,
            vj_fullscreen=False,
            debug_frame=False,
            screenshot=False,
            start_with_overlay=False,
        )
        with patch("parrot.headless_dmx_bridge.run_headless_dmx_bridge") as run_bridge:
            run(args)
        run_bridge.assert_called_once_with(args)

    def test_run_windowed_uses_gl_app(self):
        args = argparse.Namespace(
            windowed=True,
            vj_fullscreen=False,
            debug_frame=False,
            screenshot=False,
            start_with_overlay=False,
        )
        with patch("parrot.gl_window_app.run_gl_window_app") as run_window:
            run(args)
        run_window.assert_called_once_with(args)


if __name__ == "__main__":
    unittest.main()
