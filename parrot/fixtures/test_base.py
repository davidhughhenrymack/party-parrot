import pytest
from unittest.mock import MagicMock
from parrot.fixtures.base import (
    FixtureBase,
    FixtureWithBulbs,
    FixtureGroup,
    ManualGroup,
    ColorWheelEntry,
    GoboWheelEntry,
)
from parrot.utils.colour import Color


class TestFixtureBase:
    def setup_method(self):
        """Setup for each test method"""
        self.fixture = FixtureBase(address=1, name="Test Fixture", width=3)

    def test_initialization(self):
        """Test that a fixture initializes correctly"""
        assert self.fixture.address == 1
        assert self.fixture.name == "Test Fixture"
        assert self.fixture.width == 3
        assert len(self.fixture.values) == 3
        assert self.fixture.color_value == Color("black")
        assert self.fixture.dimmer_value == 0
        assert self.fixture.strobe_value == 0
        assert self.fixture.speed_value == 0
        assert self.fixture.x is None
        assert self.fixture.y is None

    def test_color_setting(self):
        """Test color setting and getting"""
        test_color = Color("red")
        self.fixture.set_color(test_color)
        assert self.fixture.get_color() == test_color

    def test_dimmer_setting(self):
        """Test dimmer setting and getting"""
        self.fixture.set_dimmer(128)
        assert self.fixture.get_dimmer() == 128

    def test_strobe_setting(self):
        """Test strobe setting and getting"""
        self.fixture.set_strobe(200)
        assert self.fixture.get_strobe() == 200

    def test_strobe_max_behavior(self):
        """Test that strobe uses max(existing, new) for highest-takes-precedence"""
        # Reset strobe first
        self.fixture.begin()
        assert self.fixture.get_strobe() == 0
        
        # Set a lower value first
        self.fixture.set_strobe(100)
        assert self.fixture.get_strobe() == 100
        
        # Set a higher value - should take precedence
        self.fixture.set_strobe(200)
        assert self.fixture.get_strobe() == 200
        
        # Set a lower value - should not override
        self.fixture.set_strobe(150)
        assert self.fixture.get_strobe() == 200
        
        # Reset and verify
        self.fixture.begin()
        assert self.fixture.get_strobe() == 0

    def test_speed_setting(self):
        """Test speed setting and getting"""
        self.fixture.set_speed(150)
        assert self.fixture.get_speed() == 150

    def test_position_setting(self):
        """Test position setting and getting"""
        self.fixture.set_position(100, 200)
        x, y = self.fixture.get_position()
        assert x == 100
        assert y == 200

    def test_pan_tilt_methods(self):
        """Test pan and tilt methods (should do nothing in base class)"""
        # These should not raise errors
        self.fixture.set_pan(128)
        self.fixture.set_tilt(64)

    def test_render(self):
        """Test that render sets DMX values correctly"""
        dmx = MagicMock()
        self.fixture.values = [100, 150, 200]
        self.fixture.render(dmx)
        dmx.set_channel.assert_any_call(1, 100)
        dmx.set_channel.assert_any_call(2, 150)
        dmx.set_channel.assert_any_call(3, 200)

    def test_render_channel_limit(self):
        """Test that render respects DMX channel limit"""
        dmx = MagicMock()
        # Create a fixture that would exceed channel 512
        fixture = FixtureBase(address=511, name="Test", width=5)
        fixture.values = [100, 150, 200, 250, 255]
        fixture.render(dmx)

        # Should only set channels up to 512
        dmx.set_channel.assert_any_call(511, 100)
        dmx.set_channel.assert_any_call(512, 150)
        # Channels 513+ should not be called

    def test_id_property(self):
        """Test the ID property"""
        expected_id = "test-fixture@1"
        assert self.fixture.id == expected_id

    def test_str_representation(self):
        """Test string representation"""
        expected_str = "Test Fixture @ 1"
        assert str(self.fixture) == expected_str


class TestFixtureWithBulbs:
    def setup_method(self):
        """Setup for each test method"""
        # Create mock bulbs
        self.bulb1 = MagicMock()
        self.bulb2 = MagicMock()
        self.bulbs = [self.bulb1, self.bulb2]

        self.fixture = FixtureWithBulbs(
            address=10, name="Test Bulb Fixture", width=6, bulbs=self.bulbs
        )

    def test_initialization(self):
        """Test that FixtureWithBulbs initializes correctly"""
        assert self.fixture.address == 10
        assert self.fixture.name == "Test Bulb Fixture"
        assert self.fixture.width == 6
        assert len(self.fixture.bulbs) == 2

    def test_set_dimmer_propagation(self):
        """Test that dimmer setting propagates to all bulbs"""
        self.fixture.set_dimmer(150)
        assert self.fixture.get_dimmer() == 150
        self.bulb1.set_dimmer.assert_called_with(150)
        self.bulb2.set_dimmer.assert_called_with(150)

    def test_set_color_propagation(self):
        """Test that color setting propagates to all bulbs"""
        test_color = Color("green")
        self.fixture.set_color(test_color)
        assert self.fixture.get_color() == test_color
        self.bulb1.set_color.assert_called_with(test_color)
        self.bulb2.set_color.assert_called_with(test_color)

    def test_get_bulbs(self):
        """Test getting bulbs"""
        bulbs = self.fixture.get_bulbs()
        assert bulbs == self.bulbs

    def test_render(self):
        """Test render method calls bulb renders"""
        dmx = MagicMock()
        self.fixture.render(dmx)

        # Should call render_values on each bulb
        self.bulb1.render_values.assert_called_with(self.fixture.values)
        self.bulb2.render_values.assert_called_with(self.fixture.values)


class TestFixtureGroup:
    def setup_method(self):
        """Setup for each test method"""
        self.fixture1 = FixtureBase(address=1, name="Fixture 1", width=3)
        self.fixture2 = FixtureBase(address=4, name="Fixture 2", width=3)
        self.group = FixtureGroup([self.fixture1, self.fixture2])

    def test_initialization(self):
        """Test that a fixture group initializes correctly"""
        assert self.group.address == 1  # Should use lowest address
        assert len(self.group.fixtures) == 2
        assert self.group.width == 6  # Sum of fixture widths

    def test_initialization_with_name(self):
        """Test initialization with custom name"""
        group = FixtureGroup([self.fixture1, self.fixture2], name="Custom Group")
        assert group.name == "Custom Group"

    def test_initialization_empty_fixtures(self):
        """Test that empty fixture list raises error"""
        with pytest.raises(ValueError, match="must contain at least one fixture"):
            FixtureGroup([])

    def test_color_setting(self):
        """Test that color setting affects all fixtures"""
        test_color = Color("blue")
        self.group.set_color(test_color)
        assert self.fixture1.get_color() == test_color
        assert self.fixture2.get_color() == test_color

    def test_dimmer_setting(self):
        """Test that dimmer setting affects all fixtures"""
        self.group.set_dimmer(200)
        assert self.fixture1.get_dimmer() == 200
        assert self.fixture2.get_dimmer() == 200

    def test_strobe_setting(self):
        """Test that strobe setting affects all fixtures"""
        self.group.set_strobe(100)
        assert self.fixture1.get_strobe() == 100
        assert self.fixture2.get_strobe() == 100

    def test_pan_tilt_speed_setting(self):
        """Test that pan, tilt, and speed settings affect all fixtures"""
        self.group.set_pan(128)
        self.group.set_tilt(64)
        self.group.set_speed(180)

        # These should not raise errors (base fixtures have pass methods)

    def test_iteration(self):
        """Test that group can be iterated"""
        fixtures = list(self.group)
        assert fixtures == [self.fixture1, self.fixture2]

    def test_length(self):
        """Test group length"""
        assert len(self.group) == 2

    def test_indexing(self):
        """Test group indexing"""
        assert self.group[0] == self.fixture1
        assert self.group[1] == self.fixture2

    def test_render(self):
        """Test render calls render on all fixtures"""
        dmx = MagicMock()
        self.group.render(dmx)
        # Each fixture should be rendered (though base fixtures don't set channels)

    def test_str_representation(self):
        """Test string representation"""
        expected = "2 FixtureBases @ 1 (2 fixtures)"
        assert str(self.group) == expected


class TestManualGroup:
    def setup_method(self):
        """Setup for each test method"""
        self.fixture1 = FixtureBase(address=1, name="Fixture 1", width=1)
        self.fixture2 = FixtureBase(address=2, name="Fixture 2", width=1)
        self.group = ManualGroup([self.fixture1, self.fixture2])

    def test_initialization(self):
        """Test that a manual group initializes correctly"""
        assert self.group.manual_dimmer == 0
        assert self.group.name == "Manual Control Group"
        # Check that parent_group is set on fixtures
        assert self.fixture1.parent_group == self.group
        assert self.fixture2.parent_group == self.group
        # Check that fixtures are initialized with white color for house lights
        from parrot.utils.colour import Color

        white = Color("white")
        assert self.fixture1.color_value.red == white.red
        assert self.fixture1.color_value.green == white.green
        assert self.fixture1.color_value.blue == white.blue

    def test_initialization_with_custom_name(self):
        """Test initialization with custom name"""
        group = ManualGroup([self.fixture1, self.fixture2], name="Custom Manual")
        assert group.name == "Custom Manual"

    def test_manual_dimmer_setting(self):
        """Test that manual dimmer setting affects all fixtures"""
        self.group.set_manual_dimmer(0.5)
        assert self.group.manual_dimmer == 0.5
        # Fixtures store dimmer in 0-255 range
        assert self.fixture1.get_dimmer() == 127.5  # 0.5 * 255
        assert self.fixture2.get_dimmer() == 127.5
        assert self.fixture1.values[0] == 127
        assert self.fixture2.values[0] == 127

    def test_get_dimmer_override(self):
        """Test that get_dimmer returns manual dimmer value in 0-255 range"""
        self.group.set_manual_dimmer(0.8)
        # Group's get_dimmer returns 0-255 range for consistency with fixtures
        assert self.group.get_dimmer() == 204.0  # 0.8 * 255

    def test_render_applies_manual_dimmer(self):
        """Test that render applies manual dimmer before rendering"""
        dmx = MagicMock()
        self.group.set_manual_dimmer(0.6)
        self.group.render(dmx)

        # Check that dimmer values were applied (in 0-255 range)
        assert self.fixture1.dimmer_value == 153.0  # 0.6 * 255
        assert self.fixture2.dimmer_value == 153.0
        assert self.fixture1.values[0] == 153
        assert self.fixture2.values[0] == 153


class TestColorWheelEntry:
    def test_initialization(self):
        """Test ColorWheelEntry initialization"""
        color = Color("red")
        entry = ColorWheelEntry(color, 50)
        assert entry.color == color
        assert entry.dmx_value == 50


class TestGoboWheelEntry:
    def test_initialization(self):
        """Test GoboWheelEntry initialization"""
        entry = GoboWheelEntry("starburst", 100)
        assert entry.name == "starburst"
        assert entry.dmx_value == 100
