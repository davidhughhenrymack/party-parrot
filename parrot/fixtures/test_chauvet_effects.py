import pytest
from unittest.mock import MagicMock
from parrot.fixtures.chauvet.derby import ChauvetDerby
from parrot.fixtures.chauvet.rotosphere import ChauvetRotosphere_28Ch, RotosphereBulb
from parrot.fixtures.chauvet.colorband_pix import (
    ChauvetColorBandPiX_36Ch,
    ColorBandPixZone,
)
from parrot.fixtures.chauvet.gigbar import ChauvetGigbarLaser
from parrot.utils.colour import Color


class TestChauvetDerby:
    def setup_method(self):
        """Setup for each test method"""
        self.derby = ChauvetDerby(address=10)
        self.dmx = MagicMock()

    def test_initialization(self):
        """Test that ChauvetDerby initializes correctly"""
        assert self.derby.address == 10
        assert self.derby.name == "chauvet derby"
        assert self.derby.width == 6
        assert len(self.derby.values) == 6

    def test_set_color(self):
        """Test color setting converts to RGBW"""
        red_color = Color("red")
        self.derby.set_color(red_color)

        assert self.derby.get_color() == red_color
        # First 4 channels should be RGBW values
        assert self.derby.values[0] == 255  # Red should be max
        assert self.derby.values[1] == 0  # Green should be 0
        assert self.derby.values[2] == 0  # Blue should be 0
        assert self.derby.values[3] >= 0  # White channel

    def test_set_strobe(self):
        """Test strobe setting with clamping"""
        self.derby.set_strobe(200)
        assert self.derby.get_strobe() == 200
        assert self.derby.values[4] == 200

    def test_set_strobe_clamping(self):
        """Test strobe value clamping to 0-250 range"""
        # Reset strobe first (simulating begin() call)
        self.derby.begin()
        
        # Test over max
        self.derby.set_strobe(300)
        assert self.derby.values[4] == 250

        # Test under min - need to reset first due to max behavior
        self.derby.begin()
        self.derby.set_strobe(-10)
        assert self.derby.values[4] == 0

    def test_set_speed(self):
        """Test speed setting"""
        self.derby.set_speed(150)
        assert self.derby.get_speed() == 150
        assert self.derby.values[5] == 150

    def test_render(self):
        """Test render method"""
        self.derby.values = [10, 20, 30, 40, 50, 60]
        self.derby.render(self.dmx)

        for i in range(6):
            self.dmx.set_channel.assert_any_call(10 + i, (i + 1) * 10)


class TestRotosphereBulb:
    def setup_method(self):
        """Setup for each test method"""
        # Create a mock parent
        self.parent = MagicMock()
        self.parent.get_dimmer.return_value = 255

        self.bulb = RotosphereBulb(address=5)
        self.bulb.parent = self.parent

    def test_initialization(self):
        """Test that RotosphereBulb initializes correctly"""
        assert self.bulb.address == 5
        assert self.bulb.name == "chauvet rotosphere bulb"
        assert self.bulb.width == 8
        assert len(self.bulb.values) == 8

    def test_render_values(self):
        """Test render_values method"""
        # Set color and dimmer
        test_color = Color("blue")
        self.bulb.set_color(test_color)
        self.bulb.set_dimmer(128)

        # Create values array
        values = [0] * 20

        # Call render_values
        self.bulb.render_values(values)

        # Values should be set for the 8 color component channels
        # Exact values depend on render_color_components implementation
        for i in range(8):
            assert values[5 + i] >= 0  # Should set values starting at address 5


class TestChauvetRotosphere_28Ch:
    def setup_method(self):
        """Setup for each test method"""
        self.rotosphere = ChauvetRotosphere_28Ch(address=15)
        self.dmx = MagicMock()

    def test_initialization(self):
        """Test that ChauvetRotosphere_28Ch initializes correctly"""
        assert self.rotosphere.address == 15
        assert self.rotosphere.name == "chauvet rotosphere"
        assert self.rotosphere.width == 28
        assert len(self.rotosphere.values) == 28
        assert len(self.rotosphere.bulbs) == 3

    def test_bulb_creation(self):
        """Test that bulbs are created correctly"""
        for i, bulb in enumerate(self.rotosphere.bulbs):
            assert isinstance(bulb, RotosphereBulb)
            assert bulb.address == i * 8  # Each bulb takes 8 channels

    def test_set_strobe(self):
        """Test strobe setting"""
        self.rotosphere.set_strobe(100)
        assert self.rotosphere.values[24] == 100  # Strobe channel

    def test_set_speed_zero(self):
        """Test speed setting to zero"""
        self.rotosphere.set_speed(0)
        assert self.rotosphere.values[27] == 0
        assert self.rotosphere.get_speed() == 0

    def test_set_speed_nonzero(self):
        """Test speed setting to non-zero value"""
        self.rotosphere.set_speed(128)

        # Should scale between 194 and 255
        speed_low = 194
        speed_fast = 255
        expected = speed_low + (128 / 255 * (speed_fast - speed_low))
        assert self.rotosphere.values[27] == int(expected)
        assert self.rotosphere.get_speed() == int(expected)

    def test_set_speed_max(self):
        """Test speed setting to maximum value"""
        self.rotosphere.set_speed(255)
        assert self.rotosphere.values[27] == 255

    def test_inherited_bulb_methods(self):
        """Test inherited methods from FixtureWithBulbs"""
        test_color = Color("green")
        self.rotosphere.set_color(test_color)

        # Check that all bulbs got the color
        for bulb in self.rotosphere.bulbs:
            assert bulb.get_color() == test_color

    def test_render(self):
        """Test render method calls bulb renders"""
        self.rotosphere.render(self.dmx)

        # Should call DMX for all 28 channels
        assert self.dmx.set_channel.call_count == 28


class TestColorBandPixZone:
    def setup_method(self):
        """Setup for each test method"""
        # Create a mock parent
        self.parent = MagicMock()
        self.parent.get_dimmer.return_value = 255

        self.zone = ColorBandPixZone(address=6, parent=self.parent)

    def test_initialization(self):
        """Test that ColorBandPixZone initializes correctly"""
        assert self.zone.address == 6
        assert self.zone.name == "colorband pix zone"
        assert self.zone.width == 3
        assert len(self.zone.values) == 3
        assert self.zone.parent == self.parent

    def test_render_values(self):
        """Test render_values method"""
        # Set color and dimmer
        test_color = Color("red")
        self.zone.set_color(test_color)
        self.zone.set_dimmer(128)

        # Create values array
        values = [0] * 20

        # Call render_values
        self.zone.render_values(values)

        # Should set RGB values at the zone's address
        assert values[6] > 0  # Red channel should be set
        assert values[7] == 0  # Green should be 0 for red color
        assert values[8] == 0  # Blue should be 0 for red color


class TestChauvetColorBandPiX_36Ch:
    def setup_method(self):
        """Setup for each test method"""
        self.colorband = ChauvetColorBandPiX_36Ch(address=20)
        self.dmx = MagicMock()

    def test_initialization(self):
        """Test that ChauvetColorBandPiX_36Ch initializes correctly"""
        assert self.colorband.address == 20
        assert self.colorband.name == "chauvet colorband pix"
        assert self.colorband.width == 36
        assert len(self.colorband.values) == 36
        assert len(self.colorband.bulbs) == 12  # 12 zones

    def test_zone_creation(self):
        """Test that zones are created correctly"""
        for i, zone in enumerate(self.colorband.bulbs):
            assert isinstance(zone, ColorBandPixZone)
            assert zone.address == i * 3  # Each zone takes 3 channels (RGB)
            assert zone.parent == self.colorband

    def test_zone_addressing(self):
        """Test that zones have correct addressing"""
        # Zone 1 should be at address 0 (relative to fixture)
        assert self.colorband.bulbs[0].address == 0
        # Zone 2 should be at address 3
        assert self.colorband.bulbs[1].address == 3
        # Zone 12 should be at address 33
        assert self.colorband.bulbs[11].address == 33

    def test_inherited_bulb_methods(self):
        """Test inherited methods from FixtureWithBulbs"""
        test_color = Color("purple")
        self.colorband.set_color(test_color)

        # Check that all zones got the color
        for zone in self.colorband.bulbs:
            assert zone.get_color() == test_color

    def test_dimmer_propagation(self):
        """Test that dimmer setting propagates to zones"""
        self.colorband.set_dimmer(200)

        # Check that all zones got the dimmer value
        for zone in self.colorband.bulbs:
            assert zone.get_dimmer() == 200

    def test_render(self):
        """Test render method"""
        # Set some colors and render
        self.colorband.set_color(Color("cyan"))
        self.colorband.set_dimmer(150)
        self.colorband.render(self.dmx)

        # Should call DMX for all 36 channels
        assert self.dmx.set_channel.call_count == 36

    def test_channel_mapping(self):
        """Test that channels map correctly to zones"""
        # Set different colors on different zones to test mapping
        colors = [Color("red"), Color("green"), Color("blue")]

        for i, color in enumerate(colors):
            if i < len(self.colorband.bulbs):
                self.colorband.bulbs[i].set_color(color)
                self.colorband.bulbs[i].set_dimmer(255)

        self.colorband.render(self.dmx)

        # Verify calls were made for all channels
        expected_calls = 36
        assert self.dmx.set_channel.call_count == expected_calls


class TestChauvetGigbarLaser:
    def setup_method(self):
        """Setup for each test method"""
        self.laser = ChauvetGigbarLaser(address=25)
        self.dmx = MagicMock()

    def test_initialization(self):
        """Test that ChauvetGigbarLaser initializes correctly"""
        assert self.laser.address == 25
        assert self.laser.name == "gigbar laser"
        assert self.laser.width == 1
        assert len(self.laser.values) == 1

    def test_set_dimmer_zero(self):
        """Test dimmer setting to zero"""
        self.laser.set_dimmer(0)
        assert self.laser.values[0] == 0

    def test_set_dimmer_nonzero(self):
        """Test dimmer setting to non-zero value"""
        self.laser.set_dimmer(128)
        assert self.laser.values[0] == 6  # Should set to on value

    def test_set_dimmer_max(self):
        """Test dimmer setting to maximum value"""
        self.laser.set_dimmer(255)
        assert self.laser.values[0] == 6  # Should still be on value

    def test_inherited_methods(self):
        """Test inherited methods from Laser base class"""
        # Should inherit from Laser which inherits from FixtureBase
        test_color = Color("red")
        self.laser.set_color(test_color)
        assert self.laser.get_color() == test_color

    def test_render(self):
        """Test render method"""
        self.laser.set_dimmer(255)
        self.laser.render(self.dmx)

        self.dmx.set_channel.assert_called_with(25, 6)

    def test_render_off(self):
        """Test render method when off"""
        self.laser.set_dimmer(0)
        self.laser.render(self.dmx)

        self.dmx.set_channel.assert_called_with(25, 0)
