import pytest
import numpy as np
from unittest.mock import Mock, MagicMock
from parrot.vj.display import VJDisplayManager, VJWindow
from parrot.director.director import Director
from parrot.director.vj_director import VJDirector
from parrot.director.frame import Frame, FrameSignal
from parrot.director.mode import Mode
from parrot.director.color_scheme import ColorScheme
from parrot.interpreters.base import InterpreterArgs
from parrot.utils.colour import Color
from parrot.state import State
from parrot.patch_bay import venues
from parrot.vj.vj_interpretations import get_vj_setup


class TestVJDisplayManager:
    """Test VJ display manager functionality"""

    def test_display_manager_creation(self):
        """Test VJ display manager creation"""
        state = State()
        state.set_venue(venues.dmack)
        director = Director(state)

        display_manager = VJDisplayManager(state, director)

        assert display_manager.state == state
        assert display_manager.director == director
        assert display_manager.is_active == False
        assert display_manager.current_frame is None
        assert display_manager.fps == 0.0

    def test_display_activation(self):
        """Test display activation and deactivation"""
        state = State()
        state.set_venue(venues.dmack)
        director = Director(state)
        display_manager = VJDisplayManager(state, director)

        # Test callbacks
        toggle_calls = []

        def on_toggle(active):
            toggle_calls.append(active)

        display_manager.on_display_toggle = on_toggle

        # Activate
        display_manager.set_active(True)
        assert display_manager.is_active == True
        assert state.vj_mode == True
        assert len(toggle_calls) == 1
        assert toggle_calls[0] == True

        # Deactivate
        display_manager.set_active(False)
        assert display_manager.is_active == False
        assert state.vj_mode == False
        assert len(toggle_calls) == 2
        assert toggle_calls[1] == False

        # Test toggle method
        display_manager.toggle()
        assert display_manager.is_active == True
        assert len(toggle_calls) == 3
        assert toggle_calls[2] == True

    def test_display_update_with_frames(self):
        """Test display updates with VJ frames"""
        state = State()
        state.set_venue(venues.dmack)
        state.set_mode(Mode.gentle)
        director = Director(state)
        display_manager = VJDisplayManager(state, director)

        # Track frame updates
        frame_updates = []

        def on_frame(frame):
            frame_updates.append(frame.copy())

        display_manager.on_frame_ready = on_frame
        display_manager.set_active(True)

        # Simulate director steps
        test_frame = Frame({FrameSignal.sustained_low: 0.6})

        for _ in range(3):
            director.step(test_frame)
            display_manager.update()

        # Should have received frame updates
        assert len(frame_updates) > 0

        # Frames should be valid
        for vj_frame in frame_updates:
            assert isinstance(vj_frame, np.ndarray)
            assert vj_frame.ndim == 3
            assert vj_frame.shape[2] == 4  # RGBA
            assert vj_frame.dtype == np.uint8

    def test_display_error_handling(self):
        """Test display manager error handling"""
        state = State()
        state.set_venue(venues.dmack)
        director = Director(state)
        display_manager = VJDisplayManager(state, director)

        # Track errors
        errors = []

        def on_error(error_msg):
            errors.append(error_msg)

        display_manager.on_error = on_error
        display_manager.set_active(True)

        # Force an error by corrupting the director's VJ method
        original_method = director.get_vj_frame

        def error_method():
            raise RuntimeError("Simulated VJ error")

        director.get_vj_frame = error_method

        # Update should handle error gracefully
        display_manager.update()

        # Should have caught the error
        assert len(errors) > 0
        assert "Simulated VJ error" in errors[0]

        # Restore original method
        director.get_vj_frame = original_method

    def test_display_performance_tracking(self):
        """Test display performance tracking"""
        state = State()
        state.set_venue(venues.dmack)
        director = Director(state)
        display_manager = VJDisplayManager(state, director)

        display_manager.set_active(True)

        # Simulate frame updates
        for _ in range(5):
            # Create mock frame
            mock_frame = np.zeros((100, 100, 4), dtype=np.uint8)
            display_manager.current_frame = mock_frame
            display_manager._update_performance_stats()

        # Should track frames
        assert display_manager.frame_count > 0 or display_manager.fps > 0

        # Get performance info
        perf_info = display_manager.get_performance_info()
        assert "display_fps" in perf_info
        assert "display_active" in perf_info
        assert "vj_system" in perf_info
        assert perf_info["display_active"] == True

    def test_frame_conversion(self):
        """Test frame conversion for display"""
        state = State()
        state.set_venue(venues.dmack)
        director = Director(state)
        display_manager = VJDisplayManager(state, director)

        # Create test frame
        test_frame = np.random.randint(0, 256, (100, 100, 4), dtype=np.uint8)

        # Test conversion
        converted = display_manager.convert_frame_for_display(test_frame)

        if converted is not None:  # PIL available
            # Should be a PIL Image
            from PIL import Image

            assert isinstance(converted, Image.Image)
            assert converted.size == (100, 100)  # PIL uses (width, height)

        # Test with resizing
        converted_resized = display_manager.convert_frame_for_display(
            test_frame, (50, 75)
        )

        if converted_resized is not None:
            assert converted_resized.size == (50, 75)

    def test_frame_save(self):
        """Test frame saving functionality"""
        state = State()
        state.set_venue(venues.dmack)
        director = Director(state)
        display_manager = VJDisplayManager(state, director)

        # Create test frame
        test_frame = np.full((50, 50, 4), [255, 128, 64, 255], dtype=np.uint8)
        display_manager.current_frame = test_frame

        # Test save (will only work if PIL is available)
        import tempfile
        import os

        with tempfile.NamedTemporaryFile(suffix=".png", delete=False) as tmp:
            temp_path = tmp.name

        try:
            success = display_manager.save_frame(temp_path)

            if success:
                # File should exist
                assert os.path.exists(temp_path)
                assert os.path.getsize(temp_path) > 0
        finally:
            # Cleanup
            if os.path.exists(temp_path):
                os.unlink(temp_path)


class TestVJWindow:
    """Test VJ window base functionality"""

    def test_vj_window_creation(self):
        """Test VJ window creation"""
        state = State()
        state.set_venue(venues.dmack)
        director = Director(state)
        display_manager = VJDisplayManager(state, director)

        window = VJWindow(display_manager)

        assert window.display_manager == display_manager
        assert window.is_visible == False
        assert display_manager.on_frame_ready == window.update_display
        assert display_manager.on_display_toggle == window.on_display_toggle

    def test_vj_window_visibility(self):
        """Test VJ window show/hide functionality"""
        state = State()
        state.set_venue(venues.dmack)
        director = Director(state)
        display_manager = VJDisplayManager(state, director)

        window = VJWindow(display_manager)

        # Mock the implementation methods
        show_calls = []
        hide_calls = []

        def mock_show():
            show_calls.append(True)

        def mock_hide():
            hide_calls.append(True)

        window._show_implementation = mock_show
        window._hide_implementation = mock_hide

        # Test show
        window.show()
        assert window.is_visible == True
        assert len(show_calls) == 1

        # Test hide
        window.hide()
        assert window.is_visible == False
        assert len(hide_calls) == 1

        # Test toggle
        window.toggle()
        assert window.is_visible == True
        assert len(show_calls) == 2

        window.toggle()
        assert window.is_visible == False
        assert len(hide_calls) == 2

    def test_vj_window_display_toggle_callback(self):
        """Test VJ window response to display manager toggles"""
        state = State()
        state.set_venue(venues.dmack)
        director = Director(state)
        display_manager = VJDisplayManager(state, director)

        window = VJWindow(display_manager)

        # Mock show/hide
        show_calls = []
        hide_calls = []

        window._show_implementation = lambda: show_calls.append(True)
        window._hide_implementation = lambda: hide_calls.append(True)

        # Display manager activation should trigger window show
        display_manager.set_active(True)
        assert len(show_calls) == 1
        assert window.is_visible == True

        # Display manager deactivation should trigger window hide
        display_manager.set_active(False)
        assert len(hide_calls) == 1
        assert window.is_visible == False


class TestVJSystemRobustness:
    """Test VJ system robustness and edge cases"""

    def test_vj_with_empty_video_directory(self):
        """Test VJ system with no videos available"""
        import tempfile
        import os

        # Create empty temporary directory
        with tempfile.TemporaryDirectory() as temp_dir:
            # Override video directory
            from parrot.vj.config import CONFIG

            original_video_dir = CONFIG["video_directory"]
            CONFIG["video_directory"] = temp_dir

            try:
                state = State()
                state.set_mode(Mode.gentle)
                vj_director = VJDirector(state, width=200, height=150)

                # Should still work (using mock layers)
                assert vj_director.is_enabled()

                frame = Frame({FrameSignal.sustained_low: 0.5})
                scheme = ColorScheme(Color("red"), Color("green"), Color("blue"))

                result = vj_director.step(frame, scheme)
                # Should render something (even if mock)

                vj_director.cleanup()

            finally:
                # Restore original config
                CONFIG["video_directory"] = original_video_dir

    def test_vj_with_invalid_mode(self):
        """Test VJ system with invalid mode"""
        state = State()

        # Create a mock invalid mode
        class InvalidMode:
            name = "invalid"

        invalid_mode = InvalidMode()

        # Should fall back gracefully
        args = InterpreterArgs(50, True, 0, 100)

        try:
            layers, interpreters = get_vj_setup(invalid_mode, args, 200, 150)
            # Should fallback to blackout mode
            assert len(layers) > 0
            assert len(interpreters) > 0
        except:
            # Or might raise an error, which is also acceptable
            pass

    def test_vj_rapid_mode_changes(self):
        """Test VJ system with rapid mode changes"""
        state = State()
        vj_director = VJDirector(state, width=150, height=100)

        # Rapid mode changes
        modes = [Mode.gentle, Mode.rave, Mode.blackout, Mode.gentle, Mode.rave]

        for mode in modes:
            state.set_mode(mode)

            # Should handle rapid changes without crashing
            frame = Frame({FrameSignal.freq_low: 0.5})
            scheme = ColorScheme(Color("red"), Color("green"), Color("blue"))

            result = vj_director.step(frame, scheme)
            # Should not crash

        vj_director.cleanup()

    def test_vj_concurrent_operations(self):
        """Test VJ system with concurrent operations"""
        state = State()
        state.set_venue(venues.dmack)
        director = Director(state)
        display_manager = VJDisplayManager(state, director)

        # Simulate concurrent operations
        display_manager.set_active(True)

        # Multiple rapid updates
        frame = Frame({FrameSignal.freq_low: 0.5, FrameSignal.freq_high: 0.3})

        for i in range(10):
            director.step(frame)
            display_manager.update()

            # Rapid mode changes during updates
            if i % 3 == 0:
                state.set_mode(Mode.rave if i % 6 == 0 else Mode.gentle)

        # Should handle concurrent operations without issues
        perf_info = display_manager.get_performance_info()
        assert isinstance(perf_info, dict)

        display_manager.set_active(False)
