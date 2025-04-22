import unittest
from unittest.mock import MagicMock
from parrot.fixtures.led_par import ParRGB, ParRGBAWU
from parrot.utils.colour import Color


class TestParRGB(unittest.TestCase):
    def setUp(self):
        self.par = ParRGB(1)  # Address 1
        self.dmx = MagicMock()

    def test_initialization(self):
        """Test that ParRGB initializes with correct channels"""
        self.assertEqual(self.par.width, 7)
        self.assertEqual(len(self.par.values), 7)
        self.assertEqual(self.par.address, 1)

    def test_dimmer_setting(self):
        """Test that dimmer value is set correctly"""
        self.par.set_dimmer(0.5)
        self.assertEqual(self.par.values[0], 127)  # 0.5 * 255
        self.assertEqual(self.par.get_dimmer(), 0.5)

    def test_strobe_setting(self):
        """Test that strobe value is set correctly"""
        self.par.set_strobe(0.75)
        self.assertEqual(self.par.values[4], 191)  # 0.75 * 255
        self.assertEqual(self.par.get_strobe(), 0.75)

    def test_color_setting(self):
        """Test that color values are set correctly"""
        test_color = Color("red")  # RGB(255, 0, 0)
        self.par.set_color(test_color)

        # Check RGB values
        self.assertEqual(self.par.values[1], 255)  # Red
        self.assertEqual(self.par.values[2], 0)  # Green
        self.assertEqual(self.par.values[3], 0)  # Blue

    def test_render_dmx(self):
        """Test that DMX values are rendered correctly"""
        # Set up fixture state
        self.par.set_dimmer(127)  # 50% brightness
        self.par.set_color(Color("blue"))
        self.par.set_strobe(64)  # 25% strobe

        # Render DMX values
        dmx = self.par.render_dmx()

        # Verify channel outputs
        self.assertEqual(dmx[0], 127)  # Dimmer channel
        self.assertEqual(dmx[1], 0)  # Red channel
        self.assertEqual(dmx[2], 0)  # Green channel
        self.assertEqual(dmx[3], 255)  # Blue channel
        self.assertEqual(dmx[4], 64)  # Strobe channel


class TestParRGBAWU(unittest.TestCase):
    def setUp(self):
        self.par = ParRGBAWU(1)  # Address 1
        self.dmx = MagicMock()

    def test_initialization(self):
        """Test that ParRGBAWU initializes with correct channels"""
        self.assertEqual(self.par.width, 9)
        self.assertEqual(len(self.par.values), 9)
        self.assertEqual(self.par.address, 1)

    def test_dimmer_setting(self):
        """Test that dimmer value is set correctly"""
        self.par.set_dimmer(0.5)
        self.assertEqual(self.par.values[0], 127)  # 0.5 * 255
        self.assertEqual(self.par.get_dimmer(), 0.5)

    def test_strobe_setting(self):
        """Test that strobe value is set correctly"""
        self.par.set_strobe(0.75)
        self.assertEqual(self.par.values[7], 191)  # 0.75 * 255
        self.assertEqual(self.par.get_strobe(), 0.75)

    def test_color_setting_pure(self):
        """Test that pure color values are set correctly"""
        test_color = Color("red")  # RGB(255, 0, 0)
        self.par.set_color(test_color)

        # Check RGBW values
        self.assertEqual(self.par.values[1], 255)  # Red
        self.assertEqual(self.par.values[2], 0)  # Green
        self.assertEqual(self.par.values[3], 0)  # Blue
        self.assertEqual(self.par.values[5], 0)  # White

    def test_color_setting_white(self):
        """Test that white color is handled correctly"""
        test_color = Color("white")  # RGB(255, 255, 255)
        self.par.set_color(test_color)

        # For white, the white channel should be used
        self.assertGreater(self.par.values[5], 0)  # White channel should be active

    def test_render_dmx(self):
        """Test that DMX values are rendered correctly"""
        # Set up fixture state
        self.par.set_dimmer(127)  # 50% brightness
        self.par.set_color(Color("blue"))
        self.par.set_strobe(64)  # 25% strobe

        # Render DMX values
        dmx = self.par.render_dmx()

        # Verify channel outputs
        self.assertEqual(dmx[0], 127)  # Dimmer channel
        self.assertEqual(dmx[1], 0)  # Red channel
        self.assertEqual(dmx[2], 0)  # Green channel
        self.assertEqual(dmx[3], 255)  # Blue channel
        self.assertEqual(dmx[4], 0)  # Amber channel
        self.assertEqual(dmx[5], 0)  # White channel
        self.assertEqual(dmx[6], 0)  # UV channel
        self.assertEqual(dmx[7], 64)  # Strobe channel

    def test_render_dmx_rgbawu(self):
        """Test that DMX values are rendered correctly for RGBAWU fixture"""
        # Set up fixture state
        self.par.set_dimmer(127)  # 50% brightness
        self.par.set_color(Color("blue"))
        self.par.set_strobe(64)  # 25% strobe

        # Render DMX values
        dmx = self.par.render_dmx()

        # Verify channel outputs
        self.assertEqual(dmx[0], 127)  # Dimmer channel
        self.assertEqual(dmx[1], 0)  # Red channel
        self.assertEqual(dmx[2], 0)  # Green channel
        self.assertEqual(dmx[3], 255)  # Blue channel
        self.assertEqual(dmx[4], 0)  # Amber channel
        self.assertEqual(dmx[5], 0)  # White channel
        self.assertEqual(dmx[6], 0)  # UV channel
        self.assertEqual(dmx[7], 64)  # Strobe channel


if __name__ == "__main__":
    unittest.main()
