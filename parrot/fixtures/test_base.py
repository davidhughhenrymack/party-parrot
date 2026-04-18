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
from parrot.utils.dmx_utils import Universe


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
        dmx.set_channel.assert_any_call(1, 100, universe=Universe.default)
        dmx.set_channel.assert_any_call(2, 150, universe=Universe.default)
        dmx.set_channel.assert_any_call(3, 200, universe=Universe.default)

    def test_render_channel_limit(self):
        """Test that render respects DMX channel limit of 512."""
        dmx = MagicMock()
        fixture = FixtureBase(address=511, name="Test", width=5)
        fixture.values = [100, 150, 200, 250, 255]
        fixture.render(dmx)

        dmx.set_channel.assert_any_call(511, 100, universe=Universe.default)
        dmx.set_channel.assert_any_call(512, 150, universe=Universe.default)
        # Channels above 512 must not be written. With address=511 + width=5
        # the raw indices would be 511..515, so 513/514/515 would exceed the
        # DMX universe and are clamped off by `FixtureBase.render`.
        written = {call.args[0] for call in dmx.set_channel.call_args_list}
        assert written == {511, 512}

    def test_render_clamps_float_values(self):
        """Fractional or out-of-range `values` must be clamped 0..255 by render()."""
        dmx = MagicMock()
        fixture = FixtureBase(address=1, name="Clamp", width=3)
        fixture.values = [-5, 42.8, 900]
        fixture.render(dmx)
        calls_by_channel = {
            call.args[0]: call.args[1] for call in dmx.set_channel.call_args_list
        }
        assert calls_by_channel == {1: 0, 2: 42, 3: 255}

    def test_render_honors_universe(self):
        """A fixture patched to a non-default universe must render there."""
        dmx = MagicMock()
        fixture = FixtureBase(address=1, name="Art", width=1, universe=Universe.art1)
        fixture.values = [77]
        fixture.render(dmx)
        dmx.set_channel.assert_called_once_with(1, 77, universe=Universe.art1)

    def test_id_property(self):
        """Test the ID property includes the universe suffix."""
        expected_id = "test-fixture@1:default"
        assert self.fixture.id == expected_id

    def test_str_representation(self):
        """Test string representation"""
        expected_str = "Test Fixture @ 1"
        assert str(self.fixture) == expected_str


class _SpyBulb(FixtureBase):
    """Minimal concrete FixtureBase subclass used to spy on propagation calls."""

    def __init__(self, address=0):
        super().__init__(address=address, name="spy bulb", width=4)
        self.render_values_calls: list[list[int]] = []

    def render_values(self, values):
        self.render_values_calls.append(list(values))


class TestFixtureWithBulbs:
    def setup_method(self):
        self.bulb1 = _SpyBulb()
        self.bulb2 = _SpyBulb()
        self.bulbs = [self.bulb1, self.bulb2]
        self.fixture = FixtureWithBulbs(
            address=10, name="Test Bulb Fixture", width=6, bulbs=self.bulbs
        )

    def test_initialization(self):
        assert self.fixture.address == 10
        assert self.fixture.name == "Test Bulb Fixture"
        assert self.fixture.width == 6
        assert len(self.fixture.bulbs) == 2

    def test_set_dimmer_propagation(self):
        """Dimmer level set on parent fans out to every bulb."""
        self.fixture.set_dimmer(150)
        assert self.fixture.get_dimmer() == 150
        for bulb in self.bulbs:
            assert bulb.get_dimmer() == 150

    def test_set_color_propagation(self):
        """Color set on parent fans out to every bulb."""
        test_color = Color("green")
        self.fixture.set_color(test_color)
        assert self.fixture.get_color() == test_color
        for bulb in self.bulbs:
            assert bulb.get_color() == test_color

    def test_get_bulbs(self):
        assert self.fixture.get_bulbs() == self.bulbs

    def test_render_calls_bulb_render_values_with_parent_values(self):
        """render() passes parent `.values` array to each bulb for RGBW fill-in."""
        self.fixture.values = [1, 2, 3, 4, 5, 6]
        self.fixture.render(MagicMock())
        for bulb in self.bulbs:
            assert bulb.render_values_calls == [[1, 2, 3, 4, 5, 6]]

    def test_begin_resets_parent_and_bulb_strobes(self):
        """begin() propagates through to all bulbs (sets strobe_value = 0)."""
        self.fixture.set_strobe(200)
        for bulb in self.bulbs:
            bulb.strobe_value = 200
        self.fixture.begin()
        assert self.fixture.get_strobe() == 0
        for bulb in self.bulbs:
            assert bulb.get_strobe() == 0


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
        assert self.group.name == "Manual Control Group"
        assert self.fixture1.parent_group == self.group
        assert self.fixture2.parent_group == self.group
        from parrot.utils.colour import Color

        white = Color("white")
        assert self.fixture1.color_value.red == white.red
        assert self.fixture1.color_value.green == white.green
        assert self.fixture1.color_value.blue == white.blue

    def test_initialization_with_custom_name(self):
        """Test initialization with custom name"""
        group = ManualGroup([self.fixture1, self.fixture2], name="Custom Manual")
        assert group.name == "Custom Manual"

    def test_apply_manual_levels_per_fixture(self):
        """Each fixture picks up its own level; missing ids go to 0."""
        self.fixture1.cloud_spec_id = "a"
        self.fixture2.cloud_spec_id = "b"
        self.group.apply_manual_levels({"a": 1.0, "b": 0.5})
        assert self.fixture1.get_dimmer() == 255.0
        assert self.fixture2.get_dimmer() == 127.5
        assert self.fixture1.values[0] == 255
        assert self.fixture2.values[0] == 127
        self.group.apply_manual_levels({"a": 0.25})
        assert self.fixture1.get_dimmer() == pytest.approx(63.75)
        assert self.fixture2.get_dimmer() == 0.0

    def test_render_writes_dimmer_to_values(self):
        """render propagates per-fixture dimmer into DMX value slots."""
        dmx = MagicMock()
        self.fixture1.cloud_spec_id = "a"
        self.fixture2.cloud_spec_id = "b"
        self.group.apply_manual_levels({"a": 0.6, "b": 0.2})
        self.group.render(dmx)
        assert self.fixture1.values[0] == 153
        assert self.fixture2.values[0] == 51


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
