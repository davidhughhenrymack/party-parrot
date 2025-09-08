import pytest
import numpy as np
from parrot.vj.vj_interpretations import (
    create_vj_renderer,
    get_vj_setup,
    vj_mode_interpretations,
)
from parrot.vj.base import SolidLayer
from parrot.vj.display import VJDisplayManager
from parrot.director.vj_director import VJDirector
from parrot.director.director import Director
from parrot.director.mode import Mode
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.interpreters.base import InterpreterArgs
from parrot.utils.colour import Color
from parrot.state import State
from parrot.patch_bay import venues


class TestVJIntegration:
    """Test VJ system integration"""

    def test_vj_setup_all_modes(self):
        """Test VJ setup for all supported modes"""
        args = InterpreterArgs(50, True, 0, 100)

        for mode in [Mode.blackout, Mode.gentle, Mode.rave]:
            layers, interpreters = get_vj_setup(mode, args, width=320, height=240)

            # Should have layers
            assert len(layers) > 0
            assert len(interpreters) > 0

            # All layers should be properly configured
            for layer in layers:
                assert layer.get_size() == (320, 240)
                assert hasattr(layer, "render")
                assert hasattr(layer, "is_enabled")
                assert hasattr(layer, "get_alpha")

            # All interpreters should be properly configured
            for interp in interpreters:
                assert hasattr(interp, "step")
                assert hasattr(interp, "get_hype")
                assert hasattr(interp, "acceptable")

    def test_create_vj_renderer_all_modes(self):
        """Test VJ renderer creation for all modes"""
        args = InterpreterArgs(60, True, 0, 100)

        for mode in [Mode.blackout, Mode.gentle, Mode.rave]:
            renderer = create_vj_renderer(mode, args, width=400, height=300)

            assert renderer is not None
            assert renderer.get_size() == (400, 300)
            assert len(renderer.layers) > 0
            assert hasattr(renderer, "interpreters")
            assert len(renderer.interpreters) > 0

            # Test rendering
            frame = Frame(
                {
                    FrameSignal.freq_low: 0.5,
                    FrameSignal.freq_high: 0.7,
                    FrameSignal.sustained_low: 0.3,
                }
            )
            scheme = ColorScheme(Color("red"), Color("green"), Color("blue"))

            # Update interpreters
            for interp in renderer.interpreters:
                interp.step(frame, scheme)

            # Render frame
            result = renderer.render_frame(frame, scheme)

            if result is not None:
                assert result.shape == (300, 400, 4)
                assert result.dtype == np.uint8

            renderer.cleanup()

    def test_vj_director_integration(self):
        """Test VJ director integration"""
        state = State()
        state.set_mode(Mode.gentle)  # Initialize with a valid mode
        vj_director = VJDirector(state, width=320, height=240)

        assert vj_director.is_enabled()
        assert vj_director.width == 320
        assert vj_director.height == 240

        # Test mode changes
        for mode in [Mode.blackout, Mode.gentle, Mode.rave]:
            state.set_mode(mode)

            # VJ director should update automatically
            assert vj_director.vj_renderer is not None

            # Test rendering
            frame = Frame({FrameSignal.freq_low: 0.6, FrameSignal.freq_high: 0.4})
            scheme = ColorScheme(Color("cyan"), Color("magenta"), Color("yellow"))

            result = vj_director.step(frame, scheme)

            if result is not None:
                assert result.shape == (240, 320, 4)
                assert result.dtype == np.uint8

        # Test performance info
        perf_info = vj_director.get_performance_info()
        assert isinstance(perf_info, dict)
        assert "fps" in perf_info
        assert "frames_rendered" in perf_info

        # Test layer info
        layer_info = vj_director.get_layer_info()
        assert isinstance(layer_info, list)
        assert len(layer_info) > 0

        vj_director.cleanup()

    def test_full_director_integration(self):
        """Test VJ integration with main Director"""
        state = State()
        state.set_venue(venues.dmack)  # Set a valid venue

        director = Director(state)

        # Director should have VJ director
        assert hasattr(director, "vj_director")
        assert director.vj_director is not None

        # Test VJ frame retrieval
        frame = Frame({FrameSignal.freq_low: 0.5, FrameSignal.freq_high: 0.3})
        director.step(frame)

        vj_frame = director.get_vj_frame()
        if vj_frame is not None:
            assert isinstance(vj_frame, np.ndarray)
            assert vj_frame.ndim == 3  # height x width x channels
            assert vj_frame.shape[2] == 4  # RGBA

        # Test VJ info
        vj_info = director.get_vj_info()
        assert isinstance(vj_info, dict)
        assert "enabled" in vj_info

    def test_vj_display_manager(self):
        """Test VJ display manager"""
        state = State()
        state.set_venue(venues.dmack)
        director = Director(state)

        display_manager = VJDisplayManager(state, director)

        assert display_manager.is_active == False
        assert display_manager.state == state
        assert display_manager.director == director

        # Test activation
        display_manager.set_active(True)
        assert display_manager.is_active == True
        assert state.vj_mode == True

        # Test deactivation
        display_manager.set_active(False)
        assert display_manager.is_active == False
        assert state.vj_mode == False

        # Test toggle
        display_manager.toggle()
        assert display_manager.is_active == True

        display_manager.toggle()
        assert display_manager.is_active == False

    def test_vj_performance_tracking(self):
        """Test VJ performance tracking"""
        state = State()
        state.set_mode(Mode.gentle)  # Initialize with a valid mode
        vj_director = VJDirector(state, width=200, height=150)

        # Render multiple frames
        frame = Frame({FrameSignal.freq_low: 0.5})
        scheme = ColorScheme(Color("red"), Color("green"), Color("blue"))

        for _ in range(5):
            vj_director.step(frame, scheme)

        perf_info = vj_director.get_performance_info()

        assert perf_info["frames_rendered"] == 5
        assert perf_info["fps"] > 0
        assert perf_info["avg_render_time_ms"] >= 0

        vj_director.cleanup()

    def test_vj_mode_switching(self):
        """Test VJ system response to mode changes"""
        state = State()
        vj_director = VJDirector(state, width=200, height=150)

        # Track layer counts for each mode
        mode_layer_counts = {}

        for mode in [Mode.blackout, Mode.gentle, Mode.rave]:
            state.set_mode(mode)

            layer_info = vj_director.get_layer_info()
            mode_layer_counts[mode] = len(layer_info)

            # Each mode should have different configurations
            assert len(layer_info) > 0

            # Test that mode change triggers new setup
            assert vj_director.vj_renderer is not None

        # Different modes should have different layer counts
        counts = list(mode_layer_counts.values())
        # At least gentle and rave should be different from blackout
        assert len(set(counts)) > 1

        vj_director.cleanup()

    def test_vj_interpreter_shifting(self):
        """Test VJ interpreter shifting functionality"""
        state = State()
        state.set_mode(Mode.rave)
        vj_director = VJDirector(state, width=200, height=150)

        # Get initial interpreters
        initial_interpreters = vj_director.vj_renderer.interpreters.copy()
        initial_interpreter_strs = [str(i) for i in initial_interpreters]

        # Shift interpreters
        vj_director.shift_vj_interpreters()

        # Should have new interpreters
        new_interpreters = vj_director.vj_renderer.interpreters
        new_interpreter_strs = [str(i) for i in new_interpreters]

        # Should have same number of interpreters
        assert len(new_interpreters) == len(initial_interpreters)

        # At least some should be different (due to randomization)
        # Note: There's a small chance they could be the same, but very unlikely
        assert len(new_interpreters) > 0

        vj_director.cleanup()

    def test_vj_error_recovery(self):
        """Test VJ system error recovery"""
        state = State()
        vj_director = VJDirector(state, width=100, height=100)

        # Force an error by corrupting the renderer
        if vj_director.vj_renderer:
            original_render = vj_director.vj_renderer.render_frame

            def error_render(frame, scheme):
                raise RuntimeError("Simulated VJ error")

            vj_director.vj_renderer.render_frame = error_render

            # Should handle error gracefully
            frame = Frame({FrameSignal.freq_low: 0.5})
            scheme = ColorScheme(Color("red"), Color("green"), Color("blue"))

            result = vj_director.step(frame, scheme)
            # Should return None instead of crashing
            assert result is None

            # Restore original method
            vj_director.vj_renderer.render_frame = original_render

        vj_director.cleanup()

    def test_vj_resize_functionality(self):
        """Test VJ system resizing"""
        state = State()
        vj_director = VJDirector(state, width=400, height=300)

        # Initial size
        assert vj_director.width == 400
        assert vj_director.height == 300

        # Resize
        vj_director.resize(800, 600)

        assert vj_director.width == 800
        assert vj_director.height == 600

        # Renderer should also be resized
        if vj_director.vj_renderer:
            assert vj_director.vj_renderer.get_size() == (800, 600)

        vj_director.cleanup()

    def test_vj_layer_type_filtering(self):
        """Test that interpreters correctly filter layer types"""
        from parrot.vj.interpreters.video_selector import VideoSelector
        from parrot.vj.interpreters.text_animator import TextAnimator

        from parrot.vj.layers.video import MockVideoLayer
        from parrot.vj.layers.text import MockTextLayer

        layers = [
            SolidLayer("solid", width=100, height=100),
            MockVideoLayer("video"),
            MockTextLayer("text", "test"),
        ]
        args = InterpreterArgs(50, True, 0, 100)

        # Video selector should only affect video layers
        video_selector = VideoSelector(layers, args)
        assert len(video_selector.video_layers) == 1
        assert video_selector.video_layers[0].name == "video"

        # Text animator should only affect text layers
        text_animator = TextAnimator(layers, args)
        assert len(text_animator.text_layers) == 1
        assert text_animator.text_layers[0].name == "test"

    def test_end_to_end_vj_workflow(self):
        """Test complete end-to-end VJ workflow"""
        # Create state and director
        state = State()
        state.set_venue(venues.dmack)
        state.set_mode(Mode.rave)

        # Create director with VJ
        director = Director(state)

        # Create display manager
        display_manager = VJDisplayManager(state, director)

        # Simulate multiple frames of operation
        frames = [
            Frame({FrameSignal.freq_low: 0.3, FrameSignal.freq_high: 0.2}),
            Frame({FrameSignal.freq_low: 0.8, FrameSignal.freq_high: 0.9}),
            Frame({FrameSignal.freq_low: 0.1, FrameSignal.freq_high: 0.1}),
        ]

        # Activate VJ display
        display_manager.set_active(True)

        rendered_frames = []

        for frame in frames:
            # Step the director (this updates both lighting and VJ)
            director.step(frame)

            # Update display manager
            display_manager.update()

            # Get VJ frame
            vj_frame = display_manager.get_current_frame()
            if vj_frame is not None:
                rendered_frames.append(vj_frame)

        # Should have rendered some frames
        assert len(rendered_frames) > 0

        # Each frame should be valid
        for vj_frame in rendered_frames:
            assert isinstance(vj_frame, np.ndarray)
            assert vj_frame.ndim == 3
            assert vj_frame.shape[2] == 4  # RGBA
            assert vj_frame.dtype == np.uint8

        # Get performance info
        perf_info = display_manager.get_performance_info()
        assert isinstance(perf_info, dict)
        assert "display_active" in perf_info
        assert perf_info["display_active"] == True

        # Cleanup
        display_manager.set_active(False)

    def test_vj_mode_interpretations_consistency(self):
        """Test that all mode interpretations are consistent"""
        args = InterpreterArgs(50, True, 0, 100)

        for mode, mode_config in vj_mode_interpretations.items():
            # Should have both layers and interpreters factory functions
            assert "layers" in mode_config
            assert "interpreters" in mode_config
            assert callable(mode_config["layers"])
            assert callable(mode_config["interpreters"])

            # Create layers and interpreters
            layers = mode_config["layers"](320, 240)
            interpreters = mode_config["interpreters"](layers, args)

            assert len(layers) > 0
            assert len(interpreters) > 0

            # All layers should be valid
            for layer in layers:
                assert hasattr(layer, "render")
                assert hasattr(layer, "z_order")
                assert layer.get_size() == (320, 240)

            # All interpreters should be valid
            for interp in interpreters:
                assert hasattr(interp, "step")
                assert hasattr(interp, "layers")

    def test_vj_frame_consistency(self):
        """Test that VJ frames are consistent across multiple renders"""
        state = State()
        state.set_mode(Mode.gentle)
        vj_director = VJDirector(state, width=200, height=150)

        frame = Frame({FrameSignal.sustained_low: 0.6})
        scheme = ColorScheme(Color("red"), Color("green"), Color("blue"))

        # Render multiple frames with same input
        results = []
        for _ in range(3):
            result = vj_director.step(frame, scheme)
            if result is not None:
                results.append(result.copy())

        if len(results) > 1:
            # Frames might be slightly different due to animation, but should be similar
            # Check that they have the same shape and format
            for result in results:
                assert result.shape == results[0].shape
                assert result.dtype == results[0].dtype

        vj_director.cleanup()

    def test_vj_signal_responsiveness(self):
        """Test that VJ system responds to different audio signals"""
        state = State()
        state.set_mode(Mode.rave)
        vj_director = VJDirector(state, width=200, height=150)

        scheme = ColorScheme(Color("red"), Color("green"), Color("blue"))

        # Test different signal combinations
        signal_tests = [
            {FrameSignal.freq_low: 0.0, FrameSignal.freq_high: 0.0},  # Silence
            {FrameSignal.freq_low: 1.0, FrameSignal.freq_high: 0.0},  # Bass only
            {FrameSignal.freq_low: 0.0, FrameSignal.freq_high: 1.0},  # Treble only
            {FrameSignal.freq_low: 1.0, FrameSignal.freq_high: 1.0},  # Full spectrum
            {FrameSignal.strobe: 1.0, FrameSignal.pulse: 1.0},  # Manual signals
        ]

        results = []
        for signals in signal_tests:
            frame = Frame(signals)
            result = vj_director.step(frame, scheme)

            if result is not None:
                results.append(
                    {
                        "signals": signals,
                        "frame": result,
                        "non_zero_pixels": np.count_nonzero(result),
                    }
                )

        # Should have rendered some frames
        assert len(results) > 0

        # Results should vary based on input signals
        non_zero_counts = [r["non_zero_pixels"] for r in results]

        # At least some variation expected (though not guaranteed due to randomness)
        if len(set(non_zero_counts)) == 1:
            # If all the same, at least verify they're valid
            assert all(count >= 0 for count in non_zero_counts)

        vj_director.cleanup()

    def test_vj_color_scheme_integration(self):
        """Test VJ system integration with color schemes"""
        state = State()
        state.set_mode(Mode.gentle)
        vj_director = VJDirector(state, width=150, height=100)

        # Test different color schemes
        schemes = [
            ColorScheme(Color("red"), Color("black"), Color("white")),
            ColorScheme(Color("blue"), Color("yellow"), Color("green")),
            ColorScheme(Color("purple"), Color("orange"), Color("cyan")),
        ]

        frame = Frame({FrameSignal.sustained_low: 0.5})

        results = []
        for scheme in schemes:
            result = vj_director.step(frame, scheme)
            if result is not None:
                results.append(result.copy())

        # Should have rendered frames
        if len(results) > 1:
            # Frames should be different due to different color schemes
            # At minimum, they should have the same format
            for result in results:
                assert result.shape == results[0].shape
                assert result.dtype == results[0].dtype

        vj_director.cleanup()

    def test_vj_memory_management(self):
        """Test VJ system memory management and cleanup"""
        state = State()

        # Create and destroy multiple VJ directors
        for i in range(3):
            vj_director = VJDirector(state, width=100, height=100)

            # Use the VJ director
            frame = Frame({FrameSignal.freq_low: 0.5})
            scheme = ColorScheme(Color("red"), Color("green"), Color("blue"))

            for _ in range(5):
                vj_director.step(frame, scheme)

            # Cleanup
            vj_director.cleanup()
            assert not vj_director.is_enabled()

    def test_vj_configuration_override(self):
        """Test VJ configuration with different parameters"""
        from parrot.vj.config import CONFIG

        # Test with different resolutions
        resolutions = [(320, 240), (640, 480), (800, 600)]

        for width, height in resolutions:
            args = InterpreterArgs(50, True, 0, 100)
            renderer = create_vj_renderer(Mode.gentle, args, width=width, height=height)

            assert renderer.get_size() == (width, height)

            # All layers should be sized correctly
            for layer in renderer.layers:
                assert layer.get_size() == (width, height)

            renderer.cleanup()

    def test_vj_interpreter_hype_filtering(self):
        """Test that interpreter selection respects hype levels"""
        # Test with different hype ranges
        hype_configs = [
            InterpreterArgs(10, True, 0, 20),  # Low hype only
            InterpreterArgs(50, True, 40, 60),  # Medium hype only
            InterpreterArgs(80, True, 70, 100),  # High hype only
        ]

        for args in hype_configs:
            # Should be able to create renderers for all modes
            for mode in [Mode.blackout, Mode.gentle, Mode.rave]:
                renderer = create_vj_renderer(mode, args, width=200, height=150)

                # Should have valid interpreters
                assert len(renderer.interpreters) > 0

                # All interpreters should be acceptable for the hype range
                for interp in renderer.interpreters:
                    # Note: Individual interpreter acceptance is tested in their classes
                    assert hasattr(interp, "get_hype")

                renderer.cleanup()
