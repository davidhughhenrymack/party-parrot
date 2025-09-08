import pytest
from unittest.mock import MagicMock
from parrot.fixtures.moving_head import MovingHead
from parrot.fixtures.base import GoboWheelEntry
from parrot.utils.colour import Color


class TestMovingHead:
    def setup_method(self):
        """Setup for each test method"""
        self.gobo_wheel = [
            GoboWheelEntry("open", 0),
            GoboWheelEntry("dots", 50),
            GoboWheelEntry("spiral", 100),
            GoboWheelEntry("starburst", 150),
        ]
        self.moving_head = MovingHead(
            address=10, name="Test Moving Head", width=8, gobo_wheel=self.gobo_wheel
        )
        self.dmx = MagicMock()

    def test_initialization(self):
        """Test that MovingHead initializes correctly"""
        assert self.moving_head.address == 10
        assert self.moving_head.name == "Test Moving Head"
        assert self.moving_head.width == 8
        assert len(self.moving_head.values) == 8
        assert self.moving_head.pan_angle == 0
        assert self.moving_head.tilt_angle == 0
        assert len(self.moving_head.gobo_wheel) == 4

    def test_set_pan_angle(self):
        """Test pan angle setting"""
        self.moving_head.set_pan_angle(180)
        assert self.moving_head.get_pan_angle() == 180

    def test_set_tilt_angle(self):
        """Test tilt angle setting"""
        self.moving_head.set_tilt_angle(90)
        assert self.moving_head.get_tilt_angle() == 90

    def test_gobo_wheel_property(self):
        """Test gobo wheel property access"""
        assert self.moving_head.gobo_wheel == self.gobo_wheel
        assert self.moving_head.gobo_wheel[0].name == "open"
        assert self.moving_head.gobo_wheel[1].dmx_value == 50

    def test_inherited_methods(self):
        """Test that inherited methods from FixtureBase work"""
        # Test color setting
        test_color = Color("red")
        self.moving_head.set_color(test_color)
        assert self.moving_head.get_color() == test_color

        # Test dimmer setting
        self.moving_head.set_dimmer(0.75)
        assert self.moving_head.get_dimmer() == 0.75

        # Test strobe setting
        self.moving_head.set_strobe(100)
        assert self.moving_head.get_strobe() == 100

    def test_render(self):
        """Test that render calls DMX correctly"""
        self.moving_head.values = [10, 20, 30, 40, 50, 60, 70, 80]
        self.moving_head.render(self.dmx)

        # Verify all channels are set
        for i in range(8):
            self.dmx.set_channel.assert_any_call(10 + i, (i + 1) * 10)

    def test_position_setting(self):
        """Test position setting and getting"""
        self.moving_head.set_position(100, 200)
        x, y = self.moving_head.get_position()
        assert x == 100
        assert y == 200

    def test_id_property(self):
        """Test the ID property"""
        expected_id = "test-moving-head@10"
        assert self.moving_head.id == expected_id
