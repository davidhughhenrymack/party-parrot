import pytest
from unittest.mock import MagicMock, patch
import time
from parrot.fixtures.chauvet.mover_base import ChauvetMoverBase
from parrot.fixtures.chauvet.intimidator120 import ChauvetSpot110_12Ch
from parrot.fixtures.chauvet.intimidator160 import ChauvetSpot160_12Ch
from parrot.fixtures.chauvet.move9 import ChauvetMove_9Ch
from parrot.fixtures.chauvet.rogue_beam_r2 import ChauvetRogueBeamR2
from parrot.fixtures.base import ColorWheelEntry, GoboWheelEntry
from parrot.utils.colour import Color


class TestChauvetMoverBase:
    def setup_method(self):
        """Setup for each test method"""
        # Create test color and gobo wheels
        self.color_wheel = [
            ColorWheelEntry(Color("white"), 0),
            ColorWheelEntry(Color("red"), 50),
            ColorWheelEntry(Color("blue"), 100),
        ]
        self.gobo_wheel = [
            GoboWheelEntry("open", 0),
            GoboWheelEntry("dots", 50),
            GoboWheelEntry("spiral", 100),
        ]

        # Create test DMX layout
        self.dmx_layout = {
            "pan_coarse": 0,
            "pan_fine": 1,
            "tilt_coarse": 2,
            "tilt_fine": 3,
            "speed": 4,
            "color_wheel": 5,
            "shutter": 6,
            "dimmer": 7,
            "gobo_wheel": 8,
        }

        self.mover = ChauvetMoverBase(
            patch=10,
            name="Test Mover",
            width=9,
            dmx_layout=self.dmx_layout,
            color_wheel=self.color_wheel,
            gobo_wheel=self.gobo_wheel,
            pan_lower=270,
            pan_upper=450,
            tilt_lower=0,
            tilt_upper=90,
        )
        self.dmx = MagicMock()

    def test_initialization(self):
        """Test that ChauvetMoverBase initializes correctly"""
        assert self.mover.address == 10
        assert self.mover.name == "Test Mover"
        assert self.mover.width == 9
        assert len(self.mover.values) == 9
        assert self.mover.color_wheel == self.color_wheel
        assert self.mover.gobo_wheel == self.gobo_wheel

        # Check calculated ranges
        assert self.mover.pan_lower == 270 / 540 * 255
        assert self.mover.pan_upper == 450 / 540 * 255
        assert self.mover.tilt_lower == 0 / 270 * 255
        assert self.mover.tilt_upper == 90 / 270 * 255

    def test_set_method(self):
        """Test the generic set method"""
        self.mover.set("dimmer", 128)
        assert self.mover.values[7] == 128

        # Test setting invalid channel
        self.mover.set("invalid_channel", 100)
        # Should not raise error, just ignore

    def test_set_dimmer(self):
        """Test dimmer setting"""
        self.mover.set_dimmer(128)
        assert self.mover.get_dimmer() == 128
        expected_dmx_value = 128 / 255 * self.mover.dimmer_upper
        assert self.mover.values[7] == expected_dmx_value

    def test_set_pan(self):
        """Test pan setting"""
        self.mover.set_pan(128)  # Mid position

        # Calculate expected value
        expected_projected = self.mover.pan_lower + (self.mover.pan_range * 128 / 255)
        assert self.mover.values[0] == int(expected_projected)

        # Check pan angle is set
        expected_angle = expected_projected / 255 * 540
        assert self.mover.get_pan_angle() == expected_angle

    def test_set_tilt(self):
        """Test tilt setting"""
        self.mover.set_tilt(128)  # Mid position

        # Calculate expected value
        expected_projected = self.mover.tilt_lower + (self.mover.tilt_range * 128 / 255)
        assert self.mover.values[2] == int(expected_projected)

        # Check tilt angle is set
        expected_angle = expected_projected / 255 * 270
        assert self.mover.get_tilt_angle() == expected_angle

    def test_set_speed(self):
        """Test speed setting"""
        self.mover.set_speed(200)
        assert self.mover.values[4] == 200

    def test_set_color_closest_match(self):
        """Test color setting finds closest color wheel match"""
        # Set a color close to red
        red_color = Color("red")
        self.mover.set_color(red_color)

        # Should find the red entry in color wheel
        assert self.mover.values[5] == 50  # Red DMX value
        assert self.mover.get_color() == Color(
            "red"
        )  # Should be set to exact wheel color

    def test_set_gobo_valid(self):
        """Test setting a valid gobo"""
        self.mover.set_gobo("dots")
        assert self.mover.values[8] == 50  # Dots DMX value

    def test_set_gobo_invalid(self):
        """Test setting an invalid gobo raises error"""
        with pytest.raises(ValueError, match="Unknown gobo"):
            self.mover.set_gobo("invalid_gobo")

    def test_set_strobe_low_value(self):
        """Test strobe setting with low value opens shutter"""
        self.mover.set_strobe(5)
        assert self.mover.get_strobe() == 5
        assert self.mover.values[6] == self.mover.shutter_open_value

    def test_set_strobe_high_value(self):
        """Test strobe setting with high value"""
        self.mover.set_strobe(200)
        assert self.mover.get_strobe() == 200

        # Should scale between strobe limits
        lower = self.mover.strobe_shutter_lower
        upper = self.mover.strobe_shutter_upper
        expected = lower + (upper - lower) * 200 / 255
        assert self.mover.values[6] == expected

    def test_set_shutter_open(self):
        """Test setting shutter to open position"""
        self.mover.set_shutter_open()
        assert self.mover.values[6] == self.mover.shutter_open_value

    def test_fine_channels_disabled(self):
        """Test mover with fine channels disabled"""
        mover = ChauvetMoverBase(
            patch=1,
            name="Test",
            width=9,
            dmx_layout=self.dmx_layout,
            color_wheel=self.color_wheel,
            gobo_wheel=self.gobo_wheel,
            disable_fine=True,
        )

        # Fine channels should not be set
        mover.set_pan(128)
        mover.set_tilt(128)
        # Fine channel values should remain 0
        assert mover.values[1] == 0  # pan_fine
        assert mover.values[3] == 0  # tilt_fine


class TestChauvetSpot120_12Ch:
    def setup_method(self):
        """Setup for each test method"""
        self.spot = ChauvetSpot110_12Ch(patch=20)
        self.dmx = MagicMock()

    def test_initialization(self):
        """Test initialization with default parameters"""
        assert self.spot.address == 20
        assert self.spot.name == "chauvet intimidator 120"
        assert self.spot.width == 12
        assert len(self.spot.color_wheel) == 8
        assert len(self.spot.gobo_wheel) == 8

    def test_color_wheel_entries(self):
        """Test color wheel has correct entries"""
        colors = [entry.color for entry in self.spot.color_wheel]
        assert Color("white") in colors
        assert Color("red") in colors
        assert Color("blue") in colors

    def test_gobo_wheel_entries(self):
        """Test gobo wheel has correct entries"""
        gobo_names = [entry.name for entry in self.spot.gobo_wheel]
        assert "open" in gobo_names
        assert "wood" in gobo_names
        assert "spiral" in gobo_names


class TestChauvetSpot160_12Ch:
    def setup_method(self):
        """Setup for each test method"""
        self.spot = ChauvetSpot160_12Ch(patch=30)
        self.dmx = MagicMock()

    def test_initialization(self):
        """Test initialization"""
        assert self.spot.address == 30
        assert self.spot.name == "chauvet intimidator 160"
        assert self.spot.width == 11  # Note: width is 11, not 12
        assert len(self.spot.color_wheel) == 10
        assert len(self.spot.gobo_wheel) == 10

    def test_pan_range(self):
        """Test pan range calculation"""
        # Should have 360 to 540 degree range
        expected_lower = 360 / 540 * 255
        expected_upper = 540 / 540 * 255
        assert self.spot.pan_lower == expected_lower
        assert self.spot.pan_upper == expected_upper


class TestChauvetMove_9Ch:
    def setup_method(self):
        """Setup for each test method"""
        self.move = ChauvetMove_9Ch(patch=40)
        self.dmx = MagicMock()

    def test_initialization(self):
        """Test initialization"""
        assert self.move.address == 40
        assert self.move.name == "chauvet move"
        assert self.move.width == 12  # Note: width is 12, not 9
        assert len(self.move.color_wheel) == 9
        assert len(self.move.gobo_wheel) == 10

    def test_dmx_layout(self):
        """Test DMX layout is correct"""
        # Test that setting values works with the layout
        self.move.set_dimmer(128)
        self.move.set_pan(100)
        self.move.set_tilt(150)

        # Values should be set in correct channels
        assert self.move.values[7] > 0  # Dimmer channel
        assert self.move.values[0] > 0  # Pan channel
        assert self.move.values[2] > 0  # Tilt channel


class TestChauvetRogueBeamR2:
    def setup_method(self):
        """Setup for each test method"""
        self.rogue = ChauvetRogueBeamR2(patch=50)
        self.dmx = MagicMock()

    def test_initialization(self):
        """Test initialization"""
        assert self.rogue.address == 50
        assert self.rogue.name == "chauvet rogue beam r2"
        assert self.rogue.width == 15
        assert len(self.rogue.color_wheel) > 0
        assert len(self.rogue.gobo_wheel) > 0

        # Check startup sequence state
        assert not self.rogue._startup_sequence_started
        assert not self.rogue._startup_sequence_complete

    def test_startup_sequence_initialization(self):
        """Test that control channel is set for startup"""
        # Should be set to disable blackout function initially
        assert self.rogue.values[14] == self.rogue.control_disable_blackout_on_all_fn

    @patch("time.time")
    def test_render_startup_sequence_start(self, mock_time):
        """Test startup sequence beginning"""
        mock_time.return_value = 1000.0

        # First render should start sequence
        self.rogue.render(self.dmx)

        assert self.rogue._startup_sequence_started
        assert not self.rogue._startup_sequence_complete
        assert self.rogue.values[14] == self.rogue.control_lamp_on

    @patch("time.time")
    def test_render_startup_sequence_middle(self, mock_time):
        """Test startup sequence middle phase"""
        # Simulate time progression
        mock_time.return_value = 1000.0
        self.rogue.render(self.dmx)  # Start sequence

        mock_time.return_value = 1002.0  # 2 seconds later
        self.rogue.render(self.dmx)

        # Should switch to disable blackout
        assert self.rogue.values[14] == self.rogue.control_disable_blackout_on_all_fn

    @patch("time.time")
    def test_render_startup_sequence_complete(self, mock_time):
        """Test startup sequence completion"""
        # Simulate time progression
        mock_time.return_value = 1000.0
        self.rogue.render(self.dmx)  # Start sequence

        mock_time.return_value = 1005.0  # 5 seconds later (past 4 second threshold)
        self.rogue.render(self.dmx)

        # Sequence should be complete
        assert self.rogue._startup_sequence_complete
        assert self.rogue.values[14] == 0  # Control channel cleared

    def test_color_wheel_has_expected_colors(self):
        """Test that color wheel contains expected colors"""
        color_names = [entry.color for entry in self.rogue.color_wheel]
        # Should contain basic colors
        assert any(
            color.red > 0.5 and color.green < 0.5 and color.blue < 0.5
            for color in color_names
        )  # Red-ish
        assert any(
            color.red < 0.5 and color.green < 0.5 and color.blue > 0.5
            for color in color_names
        )  # Blue-ish

    def test_gobo_wheel_has_expected_gobos(self):
        """Test that gobo wheel contains expected gobos"""
        gobo_names = [entry.name for entry in self.rogue.gobo_wheel]
        assert "open" in gobo_names
        assert "starburst" in gobo_names

    def test_shutter_settings(self):
        """Test shutter-specific settings"""
        # Rogue Beam R2 has different shutter settings
        assert self.rogue.shutter_open_value == 255
        assert self.rogue.strobe_shutter_lower == 16
        assert self.rogue.strobe_shutter_upper == 131

    def test_dimmer_upper_limit(self):
        """Test dimmer upper limit"""
        assert self.rogue.dimmer_upper == 200  # Custom dimmer limit
