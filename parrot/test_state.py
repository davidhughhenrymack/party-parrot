import pytest
import json
import os
import tempfile
from unittest.mock import Mock, patch, MagicMock
from parrot.state import State
from parrot.director.mode import Mode
from parrot.director.themes import themes


class TestState:
    def setup_method(self):
        """Set up test fixtures before each test method."""
        # Use a temporary directory for state files during testing
        self.temp_dir = tempfile.mkdtemp()
        self.original_cwd = os.getcwd()
        os.chdir(self.temp_dir)

    def teardown_method(self):
        """Clean up after each test method."""
        os.chdir(self.original_cwd)
        # Clean up temp files
        if os.path.exists("state.json"):
            os.remove("state.json")

    def test_state_initialization(self):
        """Test that State initializes with correct default values."""
        state = State()

        assert state.mode is None
        assert state.hype == 30
        assert state.theme == themes[0]
        assert state.manual_dimmer == 0
        assert state.hype_limiter is False
        assert state.show_waveform is True
        assert hasattr(state, "events")
        assert hasattr(state, "signal_states")

    def test_set_mode(self):
        """Test setting mode triggers events."""
        state = State()
        mock_handler = Mock()
        state.events.on_mode_change += mock_handler

        state.set_mode(Mode.rave)

        assert state.mode == Mode.rave
        mock_handler.assert_called_once_with(Mode.rave)

    def test_set_mode_same_value_no_event(self):
        """Test setting same mode doesn't trigger events."""
        state = State()
        state.set_mode(Mode.rave)

        mock_handler = Mock()
        state.events.on_mode_change += mock_handler

        state.set_mode(Mode.rave)  # Same value

        mock_handler.assert_not_called()

    def test_set_mode_thread_safe(self):
        """Test thread-safe mode setting."""
        state = State()

        state.set_mode_thread_safe(Mode.gentle)

        assert state.mode == Mode.gentle

    def test_set_hype(self):
        """Test setting hype value triggers events."""
        state = State()
        mock_handler = Mock()
        state.events.on_hype_change += mock_handler

        state.set_hype(75.0)

        assert state.hype == 75.0
        mock_handler.assert_called_once_with(75.0)

    def test_set_theme(self):
        """Test setting theme triggers events."""
        state = State()
        mock_handler = Mock()
        state.events.on_theme_change += mock_handler

        new_theme = themes[1] if len(themes) > 1 else themes[0]
        state.set_theme(new_theme)

        assert state.theme == new_theme
        mock_handler.assert_called_once_with(new_theme)

    def test_set_manual_dimmer(self):
        """Test setting manual dimmer triggers events."""
        state = State()
        mock_handler = Mock()
        state.events.on_manual_dimmer_change += mock_handler

        state.set_manual_dimmer(0.5)

        assert state.manual_dimmer == 0.5
        mock_handler.assert_called_once_with(0.5)

    def test_set_hype_limiter(self):
        """Test setting hype limiter triggers events."""
        state = State()
        mock_handler = Mock()
        state.events.on_hype_limiter_change += mock_handler

        state.set_hype_limiter(True)

        assert state.hype_limiter is True
        mock_handler.assert_called_once_with(True)

    def test_set_show_waveform(self):
        """Test setting show waveform triggers events."""
        state = State()
        mock_handler = Mock()
        state.events.on_show_waveform_change += mock_handler

        state.set_show_waveform(False)

        assert state.show_waveform is False
        mock_handler.assert_called_once_with(False)

    def test_save_state(self):
        """Test saving state to JSON file."""
        state = State()
        state.set_hype(50.0)
        state.set_manual_dimmer(0.8)
        state.set_hype_limiter(True)
        state.set_show_waveform(False)

        state.save_state()

        assert os.path.exists("state.json")

        with open("state.json", "r") as f:
            saved_data = json.load(f)

        assert saved_data["hype"] == 50
        assert saved_data["manual_dimmer"] == 0  # Should be reset to 0
        assert saved_data["hype_limiter"] is True
        assert saved_data["show_waveform"] is False

    def test_load_state_file_not_exists(self):
        """Test loading state when file doesn't exist."""
        state = State()
        # Should not raise an exception
        assert state.hype == 30  # Default value

    def test_load_state_with_valid_file(self):
        """Test loading state from valid JSON file."""
        test_data = {
            "hype": 75,
            "theme_name": themes[0].name if hasattr(themes[0], "name") else None,
            "manual_dimmer": 0.6,
            "hype_limiter": True,
            "show_waveform": False,
        }

        with open("state.json", "w") as f:
            json.dump(test_data, f)

        state = State()

        assert state.hype == 75
        assert state.manual_dimmer == 0.6
        assert state.hype_limiter is True
        assert state.show_waveform is False

    def test_load_state_with_invalid_json(self):
        """Test loading state with invalid JSON doesn't crash."""
        with open("state.json", "w") as f:
            f.write("invalid json")

        # Should not raise an exception
        state = State()
        assert state.hype == 30  # Should use default

    @patch("parrot.director.frame.FrameSignal")
    def test_set_effect_thread_safe(self, mock_frame_signal):
        """Test thread-safe effect setting."""
        state = State()
        mock_signal = Mock()
        mock_frame_signal.__getitem__.return_value = mock_signal

        # Mock the signal_states.set_signal method
        state.signal_states.set_signal = Mock()

        state.set_effect_thread_safe("strobe")

        mock_frame_signal.__getitem__.assert_called_once_with("strobe")
        state.signal_states.set_signal.assert_called_once_with(mock_signal, 1.0)

    def test_process_gui_updates_empty_queue(self):
        """Test processing GUI updates with empty queue."""
        state = State()
        # Should not raise an exception
        state.process_gui_updates()

    def test_process_gui_updates_with_mode_update(self):
        """Test processing GUI updates with mode change."""
        state = State()

        # Add a mode update to the queue
        state._gui_update_queue.put(("mode", Mode.rave))

        # Mock GUI event handler
        mock_gui_handler = Mock()
        mock_gui_handler.__module__ = "parrot.gui.something"
        state.events.on_mode_change += mock_gui_handler

        state.process_gui_updates()

        assert state.mode == Mode.rave
        mock_gui_handler.assert_called_once_with(Mode.rave)
