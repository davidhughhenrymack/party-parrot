import pytest
from unittest.mock import MagicMock
from parrot.fixtures.chauvet.par import ChauvetParRGBAWU
from parrot.fixtures.chauvet.slimpar_pro_q import ChauvetSlimParProQ_5Ch
from parrot.fixtures.chauvet.slimpar_pro_h import ChauvetSlimParProH_7Ch
from parrot.utils.colour import Color


class TestChauvetParRGBAWU:
    def setup_method(self):
        """Setup for each test method"""
        self.par = ChauvetParRGBAWU(address=10)
        self.dmx = MagicMock()

    def test_initialization(self):
        """Test that ChauvetParRGBAWU initializes correctly"""
        assert self.par.address == 10
        assert self.par.name == "chauvet par rgbwu"
        assert self.par.width == 7
        assert len(self.par.values) == 7

    def test_set_color_red(self):
        """Test color setting with red"""
        red_color = Color("red")
        self.par.set_color(red_color)

        assert self.par.get_color() == red_color
        assert self.par.values[0] == 255  # Red channel
        assert self.par.values[1] == 0  # Green channel
        assert self.par.values[2] == 0  # Blue channel
        assert self.par.values[4] == 0  # White channel
        assert self.par.values[5] == 0  # Blue duplicate

    def test_set_color_white(self):
        """Test color setting with white"""
        white_color = Color("white")
        self.par.set_color(white_color)

        assert self.par.get_color() == white_color
        # White should activate the white channel
        assert self.par.values[4] > 0  # White channel should be active

    def test_set_strobe(self):
        """Test strobe setting"""
        self.par.set_strobe(200)
        assert self.par.get_strobe() == 200
        assert self.par.values[6] == 200  # Strobe channel

    def test_set_strobe_clamping(self):
        """Test strobe value clamping"""
        # Reset strobe first (simulating begin() call)
        self.par.begin()
        
        self.par.set_strobe(300)  # Over max
        assert self.par.values[6] == 250  # Should be clamped to 250

        # Test under min - need to reset first due to max behavior
        self.par.begin()
        self.par.set_strobe(-10)  # Under min
        assert self.par.values[6] == 0  # Should be clamped to 0

    def test_render(self):
        """Test render method"""
        self.par.values = [10, 20, 30, 40, 50, 60, 70]
        self.par.render(self.dmx)

        for i in range(7):
            self.dmx.set_channel.assert_any_call(10 + i, (i + 1) * 10)


class TestChauvetSlimParProQ_5Ch:
    def setup_method(self):
        """Setup for each test method"""
        self.par = ChauvetSlimParProQ_5Ch(address=15)
        self.dmx = MagicMock()

    def test_initialization(self):
        """Test that ChauvetSlimParProQ_5Ch initializes correctly"""
        assert self.par.address == 15
        assert self.par.name == "chauvet slimpar pro q"
        assert self.par.width == 5
        assert len(self.par.values) == 5

    def test_set_color_rgb(self):
        """Test color setting with RGB values"""
        test_color = Color("blue")
        self.par.set_color(test_color)

        assert self.par.get_color() == test_color
        assert self.par.values[1] == int(test_color.red * 255)  # Red channel
        assert self.par.values[2] == int(test_color.green * 255)  # Green channel
        assert self.par.values[3] == int(test_color.blue * 255)  # Blue channel
        # Amber channel should be minimum of red and green
        assert self.par.values[4] == int(min(test_color.red, test_color.green) * 255)

    def test_set_color_amber_calculation(self):
        """Test amber channel calculation"""
        # Color with both red and green components
        yellow_color = Color("yellow")  # Should have red=1, green=1, blue=0
        self.par.set_color(yellow_color)

        # Amber should be the minimum of red and green
        expected_amber = int(min(yellow_color.red, yellow_color.green) * 255)
        assert self.par.values[4] == expected_amber

    def test_set_dimmer_exponential_curve(self):
        """Test dimmer setting with exponential curve"""
        # Test various dimmer values
        test_values = [0, 128, 255]
        for value in test_values:
            self.par.set_dimmer(value)
            expected = int(((value / 255) ** 2) * 255)
            assert self.par.values[0] == expected
            assert self.par.get_dimmer() == value

    def test_dimmer_curve_properties(self):
        """Test properties of the dimmer curve"""
        # Test that 0 maps to 0
        self.par.set_dimmer(0)
        assert self.par.values[0] == 0

        # Test that 255 maps to 255
        self.par.set_dimmer(255)
        assert self.par.values[0] == 255

        # Test that middle values are lower (exponential curve)
        self.par.set_dimmer(128)
        assert self.par.values[0] < 128  # Should be less than linear

    def test_render(self):
        """Test render method"""
        self.par.values = [50, 100, 150, 200, 250]
        self.par.render(self.dmx)

        for i in range(5):
            self.dmx.set_channel.assert_any_call(15 + i, 50 + i * 50)


class TestChauvetSlimParProH_7Ch:
    def setup_method(self):
        """Setup for each test method"""
        self.par = ChauvetSlimParProH_7Ch(address=20)
        self.dmx = MagicMock()

    def test_initialization(self):
        """Test that ChauvetSlimParProH_7Ch initializes correctly"""
        assert self.par.address == 20
        assert self.par.name == "chauvet slimpar pro h"
        assert self.par.width == 7
        assert len(self.par.values) == 7

    def test_set_dimmer_exponential_curve(self):
        """Test dimmer setting with exponential curve"""
        test_values = [0, 128, 255]
        for value in test_values:
            self.par.set_dimmer(value)
            expected = int(((value / 255) ** 2) * 255)
            assert self.par.values[0] == expected
            assert self.par.get_dimmer() == value

    def test_set_color_rgbawu(self):
        """Test color setting with RGBAWU channels"""
        test_color = Color("red")
        self.par.set_color(test_color)

        assert self.par.get_color() == test_color
        assert self.par.values[1] == int(test_color.red * 255)  # Red channel
        assert self.par.values[2] == int(test_color.green * 255)  # Green channel
        assert self.par.values[3] == int(test_color.blue * 255)  # Blue channel

        # Amber channel - minimum of red and green
        expected_amber = int(min(test_color.red, test_color.green) * 255)
        assert self.par.values[4] == expected_amber

        # White channel - minimum of RGB
        expected_white = int(
            min(test_color.red, test_color.green, test_color.blue) * 255
        )
        assert self.par.values[5] == expected_white

        # UV channel - approximation based on blue
        expected_uv = int(test_color.blue * 0.7 * 255)
        assert self.par.values[6] == expected_uv

    def test_set_color_white_channels(self):
        """Test color setting with white color"""
        white_color = Color("white")
        self.par.set_color(white_color)

        # All channels should have appropriate values for white
        assert self.par.values[1] == 255  # Red
        assert self.par.values[2] == 255  # Green
        assert self.par.values[3] == 255  # Blue
        assert self.par.values[4] == 255  # Amber (min of R,G)
        assert self.par.values[5] == 255  # White (min of R,G,B)

        # UV should be based on blue component
        expected_uv = int(white_color.blue * 0.7 * 255)
        assert self.par.values[6] == expected_uv

    def test_set_color_blue_uv(self):
        """Test UV channel calculation with blue color"""
        blue_color = Color("blue")
        self.par.set_color(blue_color)

        # UV should be 70% of blue component
        expected_uv = int(blue_color.blue * 0.7 * 255)
        assert self.par.values[6] == expected_uv

    def test_channel_mapping(self):
        """Test that channels are mapped correctly"""
        # Set a known color and verify channel mapping
        self.par.set_color(Color("cyan"))  # Should have green=1, blue=1, red=0
        self.par.set_dimmer(200)

        # Verify channel assignments
        assert self.par.values[0] == int(((200 / 255) ** 2) * 255)  # Master dimmer
        assert self.par.values[1] == 0  # Red
        assert self.par.values[2] >= 254  # Green (allow for floating point precision)
        assert self.par.values[3] == 255  # Blue
        assert self.par.values[4] == 0  # Amber (min of red, green)
        assert self.par.values[5] == 0  # White (min of RGB)
        assert self.par.values[6] == int(255 * 0.7)  # UV (70% of blue)

    def test_render(self):
        """Test render method"""
        self.par.values = [10, 20, 30, 40, 50, 60, 70]
        self.par.render(self.dmx)

        for i in range(7):
            self.dmx.set_channel.assert_any_call(20 + i, (i + 1) * 10)
