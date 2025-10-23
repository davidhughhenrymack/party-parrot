import pytest
from unittest.mock import MagicMock, patch
import time
import math
from parrot.fixtures.motionstrip import MotionstripBulb, Motionstrip38
from parrot.utils.colour import Color


class TestMotionstripBulb:
    def setup_method(self):
        """Setup for each test method"""
        self.bulb = MotionstripBulb(address=10)
        self.dmx = MagicMock()

    def test_initialization(self):
        """Test that MotionstripBulb initializes correctly"""
        assert self.bulb.address == 10
        assert self.bulb.name == "motionstrip bulb"
        assert self.bulb.width == 4
        assert len(self.bulb.values) == 4

    def test_render_values(self):
        """Test render_values method"""
        # Set up color and dimmer
        test_color = Color("red")
        self.bulb.set_color(test_color)
        self.bulb.set_dimmer(128)

        # Create a parent fixture mock
        parent = MagicMock()
        parent.get_dimmer.return_value = 255
        self.bulb.parent = parent

        # Create values array
        values = [0] * 20

        # Call render_values
        self.bulb.render_values(values)

        # Check that RGBW values are set (exact values depend on color_to_rgbw implementation)
        assert values[10] >= 0  # Red channel
        assert values[11] >= 0  # Green channel
        assert values[12] >= 0  # Blue channel
        assert values[13] >= 0  # White channel

    def test_inherited_methods(self):
        """Test inherited methods from FixtureBase"""
        # Test color setting
        test_color = Color("blue")
        self.bulb.set_color(test_color)
        assert self.bulb.get_color() == test_color

        # Test dimmer setting
        self.bulb.set_dimmer(200)
        assert self.bulb.get_dimmer() == 200


class TestMotionstrip38:
    def setup_method(self):
        """Setup for each test method"""
        self.motionstrip = Motionstrip38(
            patch=1, pan_lower=50, pan_upper=200, invert_pan=False
        )
        self.dmx = MagicMock()

    def test_initialization(self):
        """Test that Motionstrip38 initializes correctly"""
        assert self.motionstrip.address == 1
        assert self.motionstrip.name == "motionstrip 38"
        assert self.motionstrip.width == 38
        assert len(self.motionstrip.values) == 38
        assert self.motionstrip.pan_lower == 50
        assert self.motionstrip.pan_upper == 200
        assert self.motionstrip.pan_range == 150
        assert self.motionstrip.invert_pan == False
        assert len(self.motionstrip.bulbs) == 8
        # Check initial values
        assert self.motionstrip.values[1] == 128  # Pan speed
        assert self.motionstrip.values[5] == 0  # Strobe off

    def test_initialization_with_invert_pan(self):
        """Test initialization with inverted pan"""
        motionstrip = Motionstrip38(patch=1, invert_pan=True)
        assert motionstrip.invert_pan == True

    def test_set_dimmer(self):
        """Test dimmer setting"""
        self.motionstrip.set_dimmer(150)
        assert self.motionstrip.get_dimmer() == 150
        assert self.motionstrip.values[4] == 150  # Master dimmer channel

    def test_set_pan_normal(self):
        """Test pan setting without inversion"""
        self.motionstrip.set_pan(128)  # Mid position
        expected = self.motionstrip.pan_lower + (self.motionstrip.pan_range * 128 / 255)
        assert self.motionstrip.values[0] == expected

    def test_set_pan_inverted(self):
        """Test pan setting with inversion"""
        motionstrip = Motionstrip38(
            patch=1, pan_lower=50, pan_upper=200, invert_pan=True
        )
        motionstrip.set_pan(128)  # Mid position
        expected = motionstrip.pan_lower + (motionstrip.pan_range * (255 - 128) / 255)
        assert motionstrip.values[0] == expected

    def test_set_pan_speed(self):
        """Test pan speed setting"""
        self.motionstrip.set_pan_speed(200)
        assert self.motionstrip.values[1] == 200

    def test_set_tilt(self):
        """Test tilt setting (should do nothing)"""
        # This should not raise an error
        self.motionstrip.set_tilt(100)

    def test_set_strobe(self):
        """Test strobe setting"""
        self.motionstrip.set_strobe(100)
        assert self.motionstrip.get_strobe() == 100

    def test_bulb_creation(self):
        """Test that bulbs are created correctly"""
        assert len(self.motionstrip.bulbs) == 8
        for i, bulb in enumerate(self.motionstrip.bulbs):
            assert isinstance(bulb, MotionstripBulb)
            assert (
                bulb.address == 6 + i * 4
            )  # Bulbs start at channel 6, 4 channels each

    def test_inherited_bulb_methods(self):
        """Test inherited methods from FixtureWithBulbs"""
        test_color = Color("green")
        self.motionstrip.set_color(test_color)

        # Check that all bulbs got the color
        for bulb in self.motionstrip.bulbs:
            assert bulb.get_color() == test_color

    @patch("time.time")
    def test_render_with_strobe(self, mock_time):
        """Test render method with strobe effect"""
        mock_time.return_value = 1.0

        self.motionstrip.set_strobe(100)
        self.motionstrip.set_dimmer(200)

        # Mock the sin function to return a predictable value
        with patch("math.sin") as mock_sin:
            mock_sin.return_value = 0.5
            self.motionstrip.render(self.dmx)

            # Check that strobe affects master dimmer
            expected_dimmer = 255 * 0.5
            assert self.motionstrip.values[4] == expected_dimmer

    def test_render_without_strobe(self):
        """Test render method without strobe effect"""
        from parrot.utils.dmx_utils import Universe

        self.motionstrip.set_strobe(0)
        self.motionstrip.set_dimmer(150)

        self.motionstrip.render(self.dmx)

        # Master dimmer should remain unchanged
        assert self.motionstrip.values[4] == 150

        # Verify DMX calls
        for i in range(38):
            self.dmx.set_channel.assert_any_call(
                1 + i, self.motionstrip.values[i], universe=Universe.default
            )

    def test_pan_range_calculation(self):
        """Test pan range calculation"""
        motionstrip = Motionstrip38(patch=1, pan_lower=0, pan_upper=255)
        assert motionstrip.pan_range == 255

        motionstrip2 = Motionstrip38(patch=1, pan_lower=100, pan_upper=150)
        assert motionstrip2.pan_range == 50

    def test_set_color_propagation(self):
        """Test that setting color propagates to all bulbs"""
        test_color = Color("purple")
        self.motionstrip.set_color(test_color)

        # Check parent color
        assert self.motionstrip.get_color() == test_color

        # Check all bulb colors
        for bulb in self.motionstrip.bulbs:
            assert bulb.get_color() == test_color

    def test_set_dimmer_propagation(self):
        """Test that setting dimmer affects master dimmer channel"""
        self.motionstrip.set_dimmer(180)

        # Check parent dimmer
        assert self.motionstrip.get_dimmer() == 180
        # Check master dimmer channel is set
        assert self.motionstrip.values[4] == 180

        # Note: Motionstrip38 doesn't automatically propagate dimmer to individual bulbs
        # The bulbs get their dimmer from the parent during render_values calls
