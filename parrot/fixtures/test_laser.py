import pytest
from unittest.mock import MagicMock
from parrot.fixtures.laser import Laser
from parrot.fixtures.oultia.laser import TwoBeamLaser
from parrot.fixtures.uking.laser import FiveBeamLaser
from parrot.fixtures.chauvet.gigbar import ChauvetGigbarLaser
from parrot.utils.colour import Color


class TestLaser:
    def test_laser_initialization(self):
        """Test that Laser base class initializes correctly"""
        laser = Laser(address=10, name="Test Laser", width=5)
        assert laser.address == 10
        assert laser.name == "Test Laser"
        assert laser.width == 5
        assert len(laser.values) == 5


class TestTwoBeamLaser:
    def setup_method(self):
        """Setup for each test method"""
        self.laser = TwoBeamLaser(address=1)
        self.dmx = MagicMock()

    def test_initialization(self):
        """Test that TwoBeamLaser initializes correctly"""
        assert self.laser.address == 1
        assert self.laser.name == "oultia 2 beam laser"
        assert self.laser.width == 10
        assert len(self.laser.values) == 10
        # Check initial pattern setting
        assert self.laser.values[1] == 14  # Pattern set to 14

    def test_set_mode(self):
        """Test mode setting"""
        self.laser.set_mode(69)
        assert self.laser.values[0] == 69

    def test_set_pattern(self):
        """Test pattern setting"""
        self.laser.set_pattern(100)
        assert self.laser.values[1] == 100

    def test_set_dimmer_zero(self):
        """Test dimmer setting to zero sets manual mode"""
        self.laser.set_dimmer(0)
        assert self.laser.values[0] == 0  # Manual mode
        assert self.laser.get_dimmer() == 0

    def test_set_dimmer_nonzero(self):
        """Test dimmer setting to non-zero activates auto mode"""
        self.laser.set_dimmer(128)
        assert self.laser.values[0] == 69  # Auto mode
        assert self.laser.get_dimmer() == 128

    def test_render(self):
        """Test that render calls DMX correctly"""
        self.laser.values = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]
        self.laser.render(self.dmx)

        # Verify all channels are set
        for i in range(10):
            self.dmx.set_channel.assert_any_call(1 + i, i + 1)


class TestFiveBeamLaser:
    def setup_method(self):
        """Setup for each test method"""
        self.laser = FiveBeamLaser(address=5)
        self.dmx = MagicMock()

    def test_initialization(self):
        """Test that FiveBeamLaser initializes correctly"""
        assert self.laser.address == 5
        assert self.laser.name == "uking 5 beam laser"
        assert self.laser.width == 13
        assert len(self.laser.values) == 13
        # Check initial settings
        assert self.laser.values[0] == 0  # Manual mode
        assert self.laser.values[6] == 50  # Pattern
        assert self.laser.values[10] == 200  # Rotation

    def test_set_mode(self):
        """Test mode setting"""
        self.laser.set_mode(128)
        assert self.laser.values[0] == 128

    def test_set_pattern(self):
        """Test pattern setting"""
        self.laser.set_pattern(150)
        assert self.laser.values[6] == 150

    def test_set_dimmer(self):
        """Test dimmer setting affects all beam channels"""
        self.laser.set_dimmer(200)
        assert self.laser.get_dimmer() == 200
        # Check all beam dimmer channels
        for i in range(1, 6):  # Channels 1-5 are beam dimmers
            assert self.laser.values[i] == 200

    def test_set_pan(self):
        """Test pan setting"""
        self.laser.set_pan(100)
        assert self.laser.values[7] == 100

    def test_set_tilt(self):
        """Test tilt setting"""
        self.laser.set_tilt(150)
        assert self.laser.values[8] == 150

    def test_render(self):
        """Test that render calls DMX correctly"""
        self.laser.values = list(range(13))
        self.laser.render(self.dmx)

        # Verify all channels are set
        for i in range(13):
            self.dmx.set_channel.assert_any_call(5 + i, i)


class TestChauvetGigbarLaser:
    def setup_method(self):
        """Setup for each test method"""
        self.laser = ChauvetGigbarLaser(address=20)
        self.dmx = MagicMock()

    def test_initialization(self):
        """Test that ChauvetGigbarLaser initializes correctly"""
        assert self.laser.address == 20
        assert self.laser.name == "gigbar laser"
        assert self.laser.width == 1
        assert len(self.laser.values) == 1

    def test_set_dimmer_zero(self):
        """Test dimmer setting to zero"""
        self.laser.set_dimmer(0)
        assert self.laser.values[0] == 0

    def test_set_dimmer_nonzero(self):
        """Test dimmer setting to non-zero"""
        self.laser.set_dimmer(128)
        assert self.laser.values[0] == 6

    def test_render(self):
        """Test that render calls DMX correctly"""
        self.laser.set_dimmer(255)
        self.laser.render(self.dmx)
        self.dmx.set_channel.assert_called_with(20, 6)
