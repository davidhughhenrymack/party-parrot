import pytest
from unittest.mock import MagicMock
from parrot.fixtures.led_par import Par, ParRGB, ParRGBAWU
from parrot.utils.colour import Color


class TestPar:
    def test_par_base_class(self):
        """Test that Par base class can be instantiated"""
        par = Par(address=1, name="Test Par", width=3)
        assert par.address == 1
        assert par.name == "Test Par"
        assert par.width == 3


class TestParRGB:
    def setup_method(self):
        """Setup for each test method"""
        self.par = ParRGB(patch=1)  # Address 1
        self.dmx = MagicMock()

    def test_initialization(self):
        """Test that ParRGB initializes with correct channels"""
        assert self.par.width == 7
        assert len(self.par.values) == 7
        assert self.par.address == 1
        assert self.par.name == "led par"

    def test_dimmer_setting(self):
        """Test that dimmer value is set correctly"""
        self.par.set_dimmer(128)
        assert self.par.values[0] == 128  # Direct value
        assert self.par.get_dimmer() == 128

    def test_strobe_setting(self):
        """Test that strobe value is set correctly"""
        self.par.set_strobe(200)
        assert self.par.values[4] == 200  # Direct value
        assert self.par.get_strobe() == 200

    def test_color_setting(self):
        """Test that color values are set correctly"""
        test_color = Color("red")  # RGB(1, 0, 0)
        self.par.set_color(test_color)

        # Check RGB values
        assert self.par.values[1] == 255  # Red
        assert self.par.values[2] == 0  # Green
        assert self.par.values[3] == 0  # Blue
        assert self.par.get_color() == test_color

    def test_set_gobo(self):
        """Test that set_gobo does nothing (pass method)"""
        # Should not raise an error
        self.par.set_gobo("test")

    def test_render(self):
        """Test render method"""
        from parrot.utils.dmx_utils import Universe

        self.par.values = [10, 20, 30, 40, 50, 60, 70]
        self.par.render(self.dmx)

        for i in range(7):
            self.dmx.set_channel.assert_any_call(
                1 + i, (i + 1) * 10, universe=Universe.default
            )


class TestParRGBAWU:
    def setup_method(self):
        """Setup for each test method"""
        self.par = ParRGBAWU(patch=1)  # Address 1
        self.dmx = MagicMock()

    def test_initialization(self):
        """Test that ParRGBAWU initializes with correct channels"""
        assert self.par.width == 9
        assert len(self.par.values) == 9
        assert self.par.address == 1
        assert self.par.name == "par rgbawu"
        assert len(self.par.color_components) == 6

    def test_color_components(self):
        """Test that color components are defined correctly"""
        component_names = [str(c) for c in self.par.color_components]
        assert "red" in component_names
        assert "green" in component_names
        assert "blue" in component_names
        assert "white" in component_names

    def test_dimmer_setting(self):
        """Test that dimmer value is set correctly"""
        self.par.set_dimmer(128)
        assert self.par.values[0] == 128  # Direct value
        assert self.par.get_dimmer() == 128

    def test_strobe_setting(self):
        """Test that strobe value is set correctly"""
        self.par.set_strobe(200)
        assert self.par.values[7] == 200  # Direct value
        assert self.par.get_strobe() == 200

    def test_color_setting_pure(self):
        """Test that pure color values are set correctly"""
        test_color = Color("red")  # RGB(1, 0, 0)
        self.par.set_color(test_color)

        # Check RGBW values (using color_to_rgbw conversion)
        assert self.par.values[1] == 255  # Red
        assert self.par.values[2] == 0  # Green
        assert self.par.values[3] == 0  # Blue
        assert self.par.values[5] == 0  # White
        assert self.par.values[6] == 0  # Blue duplicate
        assert self.par.get_color() == test_color

    def test_color_setting_white(self):
        """Test that white color is handled correctly"""
        test_color = Color("white")  # RGB(1, 1, 1)
        self.par.set_color(test_color)

        # For white, the white channel should be used
        assert self.par.values[5] > 0  # White channel should be active

    def test_color_setting_mixed(self):
        """Test color setting with mixed color"""
        test_color = Color("yellow")  # Should have red and green components
        self.par.set_color(test_color)

        # Should have red and green components
        assert self.par.values[1] > 0  # Red
        assert self.par.values[2] > 0  # Green
        assert self.par.values[3] == 0  # Blue should be 0

    def test_render(self):
        """Test render method"""
        from parrot.utils.dmx_utils import Universe

        self.par.values = [10, 20, 30, 40, 50, 60, 70, 80, 90]
        self.par.render(self.dmx)

        for i in range(9):
            self.dmx.set_channel.assert_any_call(
                1 + i, (i + 1) * 10, universe=Universe.default
            )
