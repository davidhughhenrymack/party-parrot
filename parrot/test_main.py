import unittest
from unittest.mock import patch, MagicMock
import argparse
from parrot.main import parse_arguments
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


if __name__ == "__main__":
    unittest.main()
