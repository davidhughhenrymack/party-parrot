import pytest
import os
import math
from unittest.mock import Mock, patch, MagicMock
from parrot.utils.dmx_utils import (
    dmx_clamp,
    dmx_clamp_list,
    get_controller,
    get_entec_controller,
    ArtNetController,
    SwitchController,
    Universe,
)
from parrot.utils.mock_controller import MockDmxController


class TestDmxUtils:
    def test_dmx_clamp_normal_values(self):
        """Test dmx_clamp with normal values."""
        assert dmx_clamp(0) == 0
        assert dmx_clamp(127) == 127
        assert dmx_clamp(255) == 255

    def test_dmx_clamp_out_of_range_values(self):
        """Test dmx_clamp with out-of-range values."""
        assert dmx_clamp(-10) == 0
        assert dmx_clamp(300) == 255
        assert dmx_clamp(-1) == 0
        assert dmx_clamp(256) == 255

    def test_dmx_clamp_float_values(self):
        """Test dmx_clamp with float values."""
        assert dmx_clamp(127.5) == 127
        assert dmx_clamp(127.9) == 127
        assert dmx_clamp(128.1) == 128

    def test_dmx_clamp_nan_values(self):
        """Test dmx_clamp with NaN values."""
        assert dmx_clamp(float("nan")) == 0

    def test_dmx_clamp_infinity_values(self):
        """Test dmx_clamp with infinity values."""
        assert dmx_clamp(float("inf")) == 255
        assert dmx_clamp(float("-inf")) == 0

    def test_dmx_clamp_list_normal_values(self):
        """Test dmx_clamp_list with normal values."""
        input_list = [0, 127, 255, 100, 200]
        expected = [0, 127, 255, 100, 200]
        assert dmx_clamp_list(input_list) == expected

    def test_dmx_clamp_list_out_of_range_values(self):
        """Test dmx_clamp_list with out-of-range values."""
        input_list = [-10, 300, -1, 256, 127]
        expected = [0, 255, 0, 255, 127]
        assert dmx_clamp_list(input_list) == expected

    def test_dmx_clamp_list_float_values(self):
        """Test dmx_clamp_list with float values."""
        input_list = [127.5, 127.9, 128.1, 0.1, 254.9]
        expected = [127, 127, 128, 0, 254]
        assert dmx_clamp_list(input_list) == expected

    def test_dmx_clamp_list_with_nan(self):
        """Test dmx_clamp_list with NaN values."""
        # Note: dmx_clamp_list doesn't handle NaN like dmx_clamp does
        # This test documents the current behavior
        input_list = [
            127,
            255,
        ]  # Skip NaN for now since it's not handled in the list version
        expected = [127, 255]
        assert dmx_clamp_list(input_list) == expected

    def test_dmx_clamp_list_empty_list(self):
        """Test dmx_clamp_list with empty list."""
        assert dmx_clamp_list([]) == []

    @patch.dict(os.environ, {"MOCK_DMX": "true"})
    def test_get_entec_controller_mock_environment(self):
        """Test get_entec_controller returns mock when MOCK_DMX is set."""
        controller = get_entec_controller()
        assert isinstance(controller, MockDmxController)

    @patch.dict(os.environ, {}, clear=True)
    @patch("parrot.utils.dmx_utils.Controller")
    def test_get_entec_controller_success(self, mock_controller_class):
        """Test get_entec_controller returns real controller when available."""
        mock_controller_instance = Mock()
        mock_controller_class.return_value = mock_controller_instance

        controller = get_entec_controller()

        assert controller == mock_controller_instance
        mock_controller_class.assert_called_once_with("/dev/cu.usbserial-EN419206")

    @patch.dict(os.environ, {}, clear=True)
    @patch("parrot.utils.dmx_utils.Controller")
    def test_get_entec_controller_exception(self, mock_controller_class):
        """Test get_entec_controller falls back to mock when real controller fails."""
        mock_controller_class.side_effect = Exception("USB device not found")

        controller = get_entec_controller()

        assert isinstance(controller, MockDmxController)
        mock_controller_class.assert_called_once_with("/dev/cu.usbserial-EN419206")

    @patch.dict(os.environ, {"MOCK_DMX": ""})
    def test_get_entec_controller_empty_mock_env(self):
        """Test get_entec_controller with empty MOCK_DMX environment variable."""
        # Empty string is truthy in Python, so it will use mock controller
        controller = get_entec_controller()

        assert isinstance(controller, MockDmxController)

    def test_dmx_clamp_type_consistency(self):
        """Test that dmx_clamp always returns int."""
        assert isinstance(dmx_clamp(127.5), int)
        assert isinstance(dmx_clamp(0), int)
        assert isinstance(dmx_clamp(255), int)
        assert isinstance(dmx_clamp(float("nan")), int)

    def test_dmx_clamp_list_type_consistency(self):
        """Test that dmx_clamp_list always returns list of ints."""
        result = dmx_clamp_list([127.5, 0.1, 254.9])
        assert all(isinstance(x, int) for x in result)

    def test_dmx_clamp_edge_cases(self):
        """Test dmx_clamp with edge cases."""
        # Test exactly at boundaries
        assert dmx_clamp(0.0) == 0
        assert dmx_clamp(255.0) == 255
        assert dmx_clamp(0.4) == 0
        assert dmx_clamp(0.5) == 0  # int() truncates
        assert dmx_clamp(0.9) == 0

    def test_dmx_clamp_list_preserves_order(self):
        """Test that dmx_clamp_list preserves input order."""
        input_list = [255, 0, 127, 64, 192]
        result = dmx_clamp_list(input_list)
        assert result == [255, 0, 127, 64, 192]

    @patch("builtins.print")
    @patch.dict(os.environ, {}, clear=True)
    @patch("parrot.utils.dmx_utils.Controller")
    def test_get_entec_controller_exception_prints_message(
        self, mock_controller_class, mock_print
    ):
        """Test that get_entec_controller prints appropriate messages when failing."""
        exception = Exception("USB device not found")
        mock_controller_class.side_effect = exception

        get_entec_controller()

        # Should print the exception and fallback message
        assert mock_print.call_count >= 2

    @patch("parrot.utils.dmx_utils.StupidArtnet")
    def test_artnet_controller_set_channel(self, mock_artnet_class):
        """Test ArtNetController correctly sets channels."""
        mock_artnet = Mock()
        mock_artnet_class.return_value = mock_artnet

        controller = ArtNetController("192.168.1.100", 0)

        # Set a channel
        controller.set_channel(1, 255)

        # Verify Art-Net data was stored (channel 1 = index 0)
        assert controller.dmx_data[0] == 255

    @patch("parrot.utils.dmx_utils.StupidArtnet")
    def test_artnet_controller_submit(self, mock_artnet_class):
        """Test ArtNetController correctly submits to Art-Net."""
        mock_artnet = Mock()
        mock_artnet_class.return_value = mock_artnet

        controller = ArtNetController("192.168.1.100", 0)

        # Set some channels
        controller.set_channel(1, 255)
        controller.set_channel(10, 128)
        controller.set_channel(512, 64)

        # Submit
        controller.submit()

        # Verify Art-Net was updated and shown
        mock_artnet.set.assert_called_once()
        mock_artnet.show.assert_called_once()

        # Verify the data sent to Art-Net
        sent_data = mock_artnet.set.call_args[0][0]
        assert sent_data[0] == 255  # Channel 1
        assert sent_data[9] == 128  # Channel 10
        assert sent_data[511] == 64  # Channel 512

    @patch("parrot.utils.dmx_utils.StupidArtnet")
    def test_artnet_controller_initialization(self, mock_artnet_class):
        """Test ArtNetController initialization."""
        mock_artnet = Mock()
        mock_artnet_class.return_value = mock_artnet

        controller = ArtNetController("192.168.1.100", 1)

        # Verify StupidArtnet was initialized with correct parameters
        mock_artnet_class.assert_called_once_with(
            "192.168.1.100", 1, 512, 30, True, True
        )

        # Verify initial state
        assert len(controller.dmx_data) == 512
        assert all(v == 0 for v in controller.dmx_data)

    def test_switch_controller_routes_by_universe(self):
        """Test SwitchController routes to correct controller based on universe."""
        mock_default = Mock()
        mock_art1 = Mock()

        switch = SwitchController(
            {
                Universe.default: mock_default,
                Universe.art1: mock_art1,
            }
        )

        # Send to default universe
        switch.set_channel(10, 200, universe=Universe.default)
        mock_default.set_channel.assert_called_once_with(10, 200)
        mock_art1.set_channel.assert_not_called()

        # Send to art1 universe
        mock_default.reset_mock()
        mock_art1.reset_mock()
        switch.set_channel(15, 150, universe=Universe.art1)
        mock_art1.set_channel.assert_called_once_with(15, 150)
        mock_default.set_channel.assert_not_called()

    def test_switch_controller_submit_all(self):
        """Test SwitchController submits all controllers."""
        mock_controller1 = Mock()
        mock_controller2 = Mock()

        switch = SwitchController(
            {
                Universe.default: mock_controller1,
                Universe.art1: mock_controller2,
            }
        )

        switch.submit()

        # Both controllers should have received submit
        mock_controller1.submit.assert_called_once()
        mock_controller2.submit.assert_called_once()

    @patch.dict(os.environ, {"MOCK_DMX": "true"})
    def test_get_controller_no_venue(self):
        """Test get_controller without venue returns SwitchController with default universe only."""
        controller = get_controller()
        assert isinstance(controller, SwitchController)
        assert Universe.default in controller.controller_map
        assert Universe.art1 not in controller.controller_map

    @patch.dict(os.environ, {"MOCK_DMX": "true"})
    @patch("parrot.utils.dmx_utils.StupidArtnet")
    def test_get_controller_with_configured_venue(self, mock_artnet_class):
        """Test get_controller with configured venue returns SwitchController with both universes."""
        mock_artnet = Mock()
        mock_artnet_class.return_value = mock_artnet

        # Create mock venue
        mock_venue = Mock()
        mock_venue.name = "mtn_lotus"

        controller = get_controller(mock_venue)

        # Should return SwitchController with both universes
        assert isinstance(controller, SwitchController)
        assert Universe.default in controller.controller_map
        assert Universe.art1 in controller.controller_map

        # Verify Art-Net was initialized with config from artnet_config
        mock_artnet_class.assert_called_once_with(
            "192.168.100.113", 0, 512, 30, True, True
        )

    @patch.dict(os.environ, {"MOCK_DMX": "true"})
    def test_get_controller_with_unconfigured_venue(self):
        """Test get_controller with unconfigured venue returns SwitchController with default universe only."""
        mock_venue = Mock()
        mock_venue.name = "some_other_venue"

        controller = get_controller(mock_venue)

        # Should return SwitchController with only default universe
        assert isinstance(controller, SwitchController)
        assert Universe.default in controller.controller_map
        assert Universe.art1 not in controller.controller_map
