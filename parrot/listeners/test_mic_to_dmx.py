import pytest
import numpy as np
from unittest.mock import Mock, patch, MagicMock
from parrot.listeners.mic_to_dmx import get_rms, MicToDmx


class TestMicToDmx:
    def test_get_rms_zero_block(self):
        """Test get_rms with zero block."""
        block = np.zeros(1024)
        rms = get_rms(block)
        assert rms == 0.0

    def test_get_rms_constant_block(self):
        """Test get_rms with constant value block."""
        block = np.full(1024, 0.5)
        rms = get_rms(block)
        assert rms == 0.5

    def test_get_rms_sine_wave(self):
        """Test get_rms with sine wave."""
        # Create a sine wave
        t = np.linspace(0, 1, 1024)
        block = np.sin(2 * np.pi * 440 * t)  # 440 Hz sine wave
        rms = get_rms(block)
        # RMS of sine wave should be approximately 1/sqrt(2) ≈ 0.707
        assert abs(rms - (1 / np.sqrt(2))) < 0.01

    def test_get_rms_empty_block(self):
        """Test get_rms with empty block."""
        block = np.array([])
        rms = get_rms(block)
        assert np.isnan(rms)

    @patch("parrot.listeners.mic_to_dmx.pyaudio.PyAudio")
    @patch("parrot.listeners.mic_to_dmx.get_controller")
    @patch("parrot.listeners.mic_to_dmx.Director")
    @patch("parrot.listeners.mic_to_dmx.State")
    @patch("parrot.listeners.mic_to_dmx.SignalStates")
    def test_mic_to_dmx_initialization_no_gui(
        self,
        mock_signal_states,
        mock_state,
        mock_director,
        mock_get_controller,
        mock_pyaudio,
    ):
        """Test MicToDmx initialization without GUI."""
        # Mock arguments
        mock_args = Mock()
        mock_args.profile = False
        mock_args.no_gui = True
        mock_args.no_web = True

        # Mock dependencies
        mock_pa_instance = Mock()
        mock_pyaudio.return_value = mock_pa_instance
        mock_stream = Mock()

        mock_controller = Mock()
        mock_get_controller.return_value = mock_controller

        mock_director_instance = Mock()
        mock_director.return_value = mock_director_instance

        mock_state_instance = Mock()
        mock_state.return_value = mock_state_instance

        mock_signal_states_instance = Mock()
        mock_signal_states.return_value = mock_signal_states_instance

        with patch.object(MicToDmx, "open_mic_stream", return_value=mock_stream):
            mic_to_dmx = MicToDmx(mock_args)

        # Verify initialization
        assert mic_to_dmx.args == mock_args
        assert mic_to_dmx.pa == mock_pa_instance
        assert mic_to_dmx.stream == mock_stream
        assert mic_to_dmx.dmx == mock_controller
        assert mic_to_dmx.director == mock_director_instance
        assert mic_to_dmx.state == mock_state_instance
        assert mic_to_dmx.signal_states == mock_signal_states_instance
        assert mic_to_dmx.should_stop is False
        assert mic_to_dmx.frame_count == 0

    @patch("parrot.listeners.mic_to_dmx.pyaudio.PyAudio")
    @patch("parrot.listeners.mic_to_dmx.get_controller")
    @patch("parrot.listeners.mic_to_dmx.Director")
    @patch("parrot.listeners.mic_to_dmx.State")
    @patch("parrot.listeners.mic_to_dmx.SignalStates")
    @patch("parrot.listeners.mic_to_dmx.start_web_server")
    def test_mic_to_dmx_initialization_with_web(
        self,
        mock_start_web_server,
        mock_signal_states,
        mock_state,
        mock_director,
        mock_get_controller,
        mock_pyaudio,
    ):
        """Test MicToDmx initialization with web server."""
        # Mock arguments
        mock_args = Mock()
        mock_args.profile = False
        mock_args.no_gui = True
        mock_args.no_web = False
        mock_args.web_port = 8080

        # Mock dependencies
        mock_pa_instance = Mock()
        mock_pyaudio.return_value = mock_pa_instance
        mock_stream = Mock()

        mock_controller = Mock()
        mock_get_controller.return_value = mock_controller

        mock_director_instance = Mock()
        mock_director.return_value = mock_director_instance

        mock_state_instance = Mock()
        mock_state.return_value = mock_state_instance

        mock_signal_states_instance = Mock()
        mock_signal_states.return_value = mock_signal_states_instance

        with patch.object(MicToDmx, "open_mic_stream", return_value=mock_stream):
            mic_to_dmx = MicToDmx(mock_args)

        # Verify web server was started
        mock_start_web_server.assert_called_once_with(
            mock_state_instance, director=mock_director_instance, port=8080
        )

    @patch("parrot.listeners.mic_to_dmx.pyaudio.PyAudio")
    @patch("parrot.listeners.mic_to_dmx.get_controller")
    @patch("parrot.listeners.mic_to_dmx.Director")
    @patch("parrot.listeners.mic_to_dmx.State")
    @patch("parrot.listeners.mic_to_dmx.SignalStates")
    @patch("parrot.listeners.mic_to_dmx.tracemalloc")
    def test_mic_to_dmx_initialization_with_profiling(
        self,
        mock_tracemalloc,
        mock_signal_states,
        mock_state,
        mock_director,
        mock_get_controller,
        mock_pyaudio,
    ):
        """Test MicToDmx initialization with profiling enabled."""
        # Mock arguments
        mock_args = Mock()
        mock_args.profile = True
        mock_args.no_gui = True
        mock_args.no_web = True

        # Mock dependencies
        mock_pa_instance = Mock()
        mock_pyaudio.return_value = mock_pa_instance
        mock_stream = Mock()

        mock_controller = Mock()
        mock_get_controller.return_value = mock_controller

        mock_director_instance = Mock()
        mock_director.return_value = mock_director_instance

        mock_state_instance = Mock()
        mock_state.return_value = mock_state_instance

        mock_signal_states_instance = Mock()
        mock_signal_states.return_value = mock_signal_states_instance

        with patch.object(MicToDmx, "open_mic_stream", return_value=mock_stream):
            mic_to_dmx = MicToDmx(mock_args)

        # Verify profiling was started
        mock_tracemalloc.start.assert_called_once()

    def test_find_input_device_with_mic_keyword(self):
        """Test find_input_device finds device with 'mic' in name."""
        mock_args = Mock()
        mock_args.profile = False
        mock_args.no_gui = True
        mock_args.no_web = True

        with patch(
            "parrot.listeners.mic_to_dmx.pyaudio.PyAudio"
        ) as mock_pyaudio, patch("parrot.listeners.mic_to_dmx.get_controller"), patch(
            "parrot.listeners.mic_to_dmx.Director"
        ), patch(
            "parrot.listeners.mic_to_dmx.State"
        ), patch(
            "parrot.listeners.mic_to_dmx.SignalStates"
        ), patch.object(
            MicToDmx, "open_mic_stream"
        ):

            mock_pa_instance = Mock()
            mock_pyaudio.return_value = mock_pa_instance
            mock_pa_instance.get_device_count.return_value = 3
            mock_pa_instance.get_device_info_by_index.side_effect = [
                {"name": "Speaker"},
                {"name": "Built-in Microphone"},
                {"name": "Headphones"},
            ]

            mic_to_dmx = MicToDmx(mock_args)
            device_index = mic_to_dmx.find_input_device()

            assert device_index == 1

    def test_find_input_device_with_input_keyword(self):
        """Test find_input_device finds device with 'input' in name."""
        mock_args = Mock()
        mock_args.profile = False
        mock_args.no_gui = True
        mock_args.no_web = True

        with patch(
            "parrot.listeners.mic_to_dmx.pyaudio.PyAudio"
        ) as mock_pyaudio, patch("parrot.listeners.mic_to_dmx.get_controller"), patch(
            "parrot.listeners.mic_to_dmx.Director"
        ), patch(
            "parrot.listeners.mic_to_dmx.State"
        ), patch(
            "parrot.listeners.mic_to_dmx.SignalStates"
        ), patch.object(
            MicToDmx, "open_mic_stream"
        ):

            mock_pa_instance = Mock()
            mock_pyaudio.return_value = mock_pa_instance
            mock_pa_instance.get_device_count.return_value = 2
            mock_pa_instance.get_device_info_by_index.side_effect = [
                {"name": "Speaker"},
                {"name": "Line Input"},
            ]

            mic_to_dmx = MicToDmx(mock_args)
            device_index = mic_to_dmx.find_input_device()

            assert device_index == 1

    def test_find_input_device_no_match(self):
        """Test find_input_device returns None when no matching device found."""
        mock_args = Mock()
        mock_args.profile = False
        mock_args.no_gui = True
        mock_args.no_web = True

        with patch(
            "parrot.listeners.mic_to_dmx.pyaudio.PyAudio"
        ) as mock_pyaudio, patch("parrot.listeners.mic_to_dmx.get_controller"), patch(
            "parrot.listeners.mic_to_dmx.Director"
        ), patch(
            "parrot.listeners.mic_to_dmx.State"
        ), patch(
            "parrot.listeners.mic_to_dmx.SignalStates"
        ), patch.object(
            MicToDmx, "open_mic_stream"
        ):

            mock_pa_instance = Mock()
            mock_pyaudio.return_value = mock_pa_instance
            mock_pa_instance.get_device_count.return_value = 2
            mock_pa_instance.get_device_info_by_index.side_effect = [
                {"name": "Speaker"},
                {"name": "Headphones"},
            ]

            mic_to_dmx = MicToDmx(mock_args)
            device_index = mic_to_dmx.find_input_device()

            assert device_index is None

    def test_quit_saves_state(self):
        """Test quit method saves state and sets should_stop flag."""
        mock_args = Mock()
        mock_args.profile = False
        mock_args.no_gui = True
        mock_args.no_web = True

        with patch("parrot.listeners.mic_to_dmx.pyaudio.PyAudio"), patch(
            "parrot.listeners.mic_to_dmx.get_controller"
        ), patch("parrot.listeners.mic_to_dmx.Director"), patch(
            "parrot.listeners.mic_to_dmx.State"
        ) as mock_state, patch(
            "parrot.listeners.mic_to_dmx.SignalStates"
        ), patch.object(
            MicToDmx, "open_mic_stream"
        ):

            mock_state_instance = Mock()
            mock_state.return_value = mock_state_instance

            mic_to_dmx = MicToDmx(mock_args)
            mic_to_dmx.quit()

            assert mic_to_dmx.should_stop is True
            mock_state_instance.save_state.assert_called_once()

    @patch("parrot.listeners.mic_to_dmx.time.sleep")
    def test_run_loop_with_keyboard_interrupt(self, mock_sleep):
        """Test run method handles KeyboardInterrupt gracefully."""
        mock_args = Mock()
        mock_args.profile = False
        mock_args.no_gui = True
        mock_args.no_web = True

        with patch("parrot.listeners.mic_to_dmx.pyaudio.PyAudio"), patch(
            "parrot.listeners.mic_to_dmx.get_controller"
        ), patch("parrot.listeners.mic_to_dmx.Director"), patch(
            "parrot.listeners.mic_to_dmx.State"
        ), patch(
            "parrot.listeners.mic_to_dmx.SignalStates"
        ), patch.object(
            MicToDmx, "open_mic_stream"
        ):

            mic_to_dmx = MicToDmx(mock_args)

            # Mock listen method to raise KeyboardInterrupt
            with patch.object(mic_to_dmx, "listen", side_effect=KeyboardInterrupt):
                mic_to_dmx.run()  # Should not raise exception

    def test_open_mic_stream_calls_pyaudio_correctly(self):
        """Test open_mic_stream configures PyAudio stream correctly."""
        mock_args = Mock()
        mock_args.profile = False
        mock_args.no_gui = True
        mock_args.no_web = True

        with patch(
            "parrot.listeners.mic_to_dmx.pyaudio.PyAudio"
        ) as mock_pyaudio, patch("parrot.listeners.mic_to_dmx.get_controller"), patch(
            "parrot.listeners.mic_to_dmx.Director"
        ), patch(
            "parrot.listeners.mic_to_dmx.State"
        ), patch(
            "parrot.listeners.mic_to_dmx.SignalStates"
        ):

            mock_pa_instance = Mock()
            mock_pyaudio.return_value = mock_pa_instance
            mock_stream = Mock()
            mock_pa_instance.open.return_value = mock_stream

            with patch.object(MicToDmx, "find_input_device", return_value=1):
                mic_to_dmx = MicToDmx(mock_args)

            # Verify stream configuration
            mock_pa_instance.open.assert_called_once()
            call_args = mock_pa_instance.open.call_args
            assert call_args[1]["channels"] == 1
            assert call_args[1]["rate"] == 44100
            assert call_args[1]["input"] is True
            assert call_args[1]["input_device_index"] == 1

            # Verify stream was started
            mock_stream.start_stream.assert_called_once()
