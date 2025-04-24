import unittest
from unittest.mock import MagicMock
from parrot.director.scenes import scenes, get_scene_interpreter
from parrot.fixtures.base import FixtureBase, FixtureTag
from parrot.interpreters.base import InterpreterArgs, ColorFg
from parrot.utils.colour import Color
from parrot.interpreters.dimmer import Dimmer255
from parrot.director.color_scheme import ColorScheme


class TestScenes(unittest.TestCase):
    def setUp(self):
        self.args = InterpreterArgs(
            hype=50,  # Medium hype level
            allow_rainbows=True,  # Allow rainbow effects
            min_hype=0,  # No minimum hype requirement
            max_hype=100,  # No maximum hype limit
        )

        # Create test fixtures
        self.manual_fixture = FixtureBase(1, "Manual Fixture", 1)
        self.manual_fixture.tags = [FixtureTag.MANUAL]

        self.par_fixture = FixtureBase(10, "PAR Fixture", 1)
        self.par_fixture.tags = [FixtureTag.PAR]

        self.other_fixture = FixtureBase(20, "Other Fixture", 1)
        self.other_fixture.tags = []

        # Create a test color scheme
        self.scheme = ColorScheme(
            Color("purple"),  # fg
            Color("black"),  # bg
            Color("white"),  # bg_contrast
        )

    def test_scene_definitions(self):
        """Test that scenes are defined correctly."""
        self.assertIn("manual_fixtures", scenes)
        self.assertIn("manual_fixtures_1_9", scenes)
        self.assertIn("purple_pars", scenes)

        # Check manual_fixtures scene
        manual_scene = scenes["manual_fixtures"]
        self.assertIn(FixtureBase, manual_scene)
        self.assertEqual(len(manual_scene[FixtureBase]), 2)  # Dimmer255 and tags

        # Check manual_fixtures_1_9 scene
        manual_1_9_scene = scenes["manual_fixtures_1_9"]
        self.assertIn(FixtureBase, manual_1_9_scene)
        self.assertEqual(len(manual_1_9_scene[FixtureBase]), 2)  # Dimmer255 and tags

        # Check purple_pars scene
        purple_scene = scenes["purple_pars"]
        self.assertIn(FixtureBase, purple_scene)
        self.assertEqual(
            len(purple_scene[FixtureBase]), 3
        )  # Dimmer255, ColorFg, and tags

    def test_get_scene_interpreter(self):
        """Test getting interpreters for scenes."""
        # Test manual_fixtures scene with matching fixture
        interpreter = get_scene_interpreter(
            "manual_fixtures", [self.manual_fixture], self.args
        )
        self.assertIsNotNone(interpreter)
        self.assertEqual(interpreter.group[0], self.manual_fixture)

        # Test manual_fixtures scene with non-matching fixture
        interpreter = get_scene_interpreter(
            "manual_fixtures", [self.other_fixture], self.args
        )
        self.assertIsNone(interpreter)

        # Test purple_pars scene with matching fixture
        interpreter = get_scene_interpreter(
            "purple_pars", [self.par_fixture], self.args
        )
        self.assertIsNotNone(interpreter)
        self.assertEqual(interpreter.group[0], self.par_fixture)

        # Test purple_pars scene with non-matching fixture
        interpreter = get_scene_interpreter(
            "purple_pars", [self.other_fixture], self.args
        )
        self.assertIsNone(interpreter)

        # Test unknown scene
        with self.assertRaises(ValueError):
            get_scene_interpreter("unknown_scene", [self.manual_fixture], self.args)

    def test_manual_fixtures_1_9_filtering(self):
        """Test that manual_fixtures_1_9 scene filters by address."""
        # Create fixtures with different addresses
        fixture_1 = FixtureBase(1, "Fixture 1", 1, tags=[FixtureTag.MANUAL])
        fixture_5 = FixtureBase(5, "Fixture 5", 1, tags=[FixtureTag.MANUAL])
        fixture_10 = FixtureBase(10, "Fixture 10", 1, tags=[FixtureTag.MANUAL])

        # Test with address in range
        interpreter = get_scene_interpreter(
            "manual_fixtures_1_9", [fixture_1], self.args
        )
        self.assertIsNotNone(interpreter)
        self.assertEqual(interpreter.group[0], fixture_1)

        interpreter = get_scene_interpreter(
            "manual_fixtures_1_9", [fixture_5], self.args
        )
        self.assertIsNotNone(interpreter)
        self.assertEqual(interpreter.group[0], fixture_5)

        # Test with address out of range
        interpreter = get_scene_interpreter(
            "manual_fixtures_1_9", [fixture_10], self.args
        )
        self.assertIsNone(interpreter)

    def test_scene_dimmer_values(self):
        """Test that scene dimmer values are applied correctly."""
        # Create a fixture with a mock render method
        fixture = MagicMock(spec=FixtureBase)
        fixture.address = 1
        fixture.width = 1
        fixture.values = [0]
        fixture.tags = [FixtureTag.MANUAL]

        # Get the interpreter
        interpreter = get_scene_interpreter("manual_fixtures", [fixture], self.args)
        self.assertIsNotNone(interpreter)

        # Step the interpreter
        interpreter.step(None, None)

        # Check that the dimmer value was set to 255 (100%)
        fixture.set_dimmer.assert_called_with(255)

        # Test with a different scene
        fixture = MagicMock(spec=FixtureBase)
        fixture.address = 10
        fixture.width = 1
        fixture.values = [0]
        fixture.tags = [FixtureTag.PAR]

        interpreter = get_scene_interpreter("purple_pars", [fixture], self.args)
        self.assertIsNotNone(interpreter)

        # Step the interpreter
        interpreter.step(
            None, None
        )  # The color scheme is now handled by the interpreter itself

        # Check that both dimmer and color were set
        fixture.set_dimmer.assert_called_with(255)
        fixture.set_color.assert_called_with(Color("purple"))
