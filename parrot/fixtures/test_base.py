import unittest
from unittest.mock import MagicMock
from parrot.fixtures.base import FixtureBase, FixtureGroup, ManualGroup
from parrot.utils.colour import Color


class TestFixtureBase(unittest.TestCase):
    def setUp(self):
        self.fixture = FixtureBase(address=1, name="Test Fixture", width=3)

    def test_initialization(self):
        """Test that a fixture initializes correctly"""
        self.assertEqual(self.fixture.address, 1)
        self.assertEqual(self.fixture.name, "Test Fixture")
        self.assertEqual(self.fixture.width, 3)
        self.assertEqual(len(self.fixture.values), 3)
        self.assertEqual(self.fixture.color_value, Color("black"))
        self.assertEqual(self.fixture.dimmer_value, 0)

    def test_color_setting(self):
        """Test color setting and getting"""
        test_color = Color("red")
        self.fixture.set_color(test_color)
        self.assertEqual(self.fixture.get_color(), test_color)

    def test_dimmer_setting(self):
        """Test dimmer setting and getting"""
        self.fixture.set_dimmer(0.5)
        self.assertEqual(self.fixture.get_dimmer(), 0.5)

    def test_render(self):
        """Test that render sets DMX values correctly"""
        dmx = MagicMock()
        self.fixture.values = [100, 150, 200]
        self.fixture.render(dmx)
        dmx.set_channel.assert_any_call(1, 100)
        dmx.set_channel.assert_any_call(2, 150)
        dmx.set_channel.assert_any_call(3, 200)


class TestFixtureGroup(unittest.TestCase):
    def setUp(self):
        self.fixture1 = FixtureBase(address=1, name="Fixture 1", width=3)
        self.fixture2 = FixtureBase(address=4, name="Fixture 2", width=3)
        self.group = FixtureGroup([self.fixture1, self.fixture2])

    def test_initialization(self):
        """Test that a fixture group initializes correctly"""
        self.assertEqual(self.group.address, 1)  # Should use lowest address
        self.assertEqual(len(self.group.fixtures), 2)
        self.assertEqual(self.group.width, 6)  # Sum of fixture widths

    def test_color_setting(self):
        """Test that color setting affects all fixtures"""
        test_color = Color("blue")
        self.group.set_color(test_color)
        self.assertEqual(self.fixture1.get_color(), test_color)
        self.assertEqual(self.fixture2.get_color(), test_color)

    def test_dimmer_setting(self):
        """Test that dimmer setting affects all fixtures"""
        self.group.set_dimmer(0.75)
        self.assertEqual(self.fixture1.get_dimmer(), 0.75)
        self.assertEqual(self.fixture2.get_dimmer(), 0.75)


class TestManualGroup(unittest.TestCase):
    def setUp(self):
        self.fixture1 = FixtureBase(address=1, name="Fixture 1", width=1)
        self.fixture2 = FixtureBase(address=2, name="Fixture 2", width=1)
        self.group = ManualGroup([self.fixture1, self.fixture2])

    def test_initialization(self):
        """Test that a manual group initializes correctly"""
        self.assertEqual(self.group.manual_dimmer, 0)
        self.assertEqual(self.group.name, "Manual Control Group")

    def test_manual_dimmer_setting(self):
        """Test that manual dimmer setting affects all fixtures"""
        self.group.set_manual_dimmer(0.5)
        self.assertEqual(self.group.manual_dimmer, 0.5)
        self.assertEqual(self.fixture1.get_dimmer(), 0.5)
        self.assertEqual(self.fixture2.get_dimmer(), 0.5)
        self.assertEqual(self.fixture1.values[0], 127)  # 0.5 * 255
        self.assertEqual(self.fixture2.values[0], 127)


if __name__ == "__main__":
    unittest.main()
