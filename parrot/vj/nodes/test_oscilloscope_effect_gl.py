#!/usr/bin/env python3

import pytest
import numpy as np
import moderngl as mgl
from unittest.mock import Mock

from parrot.vj.nodes.oscilloscope_effect import OscilloscopeEffect
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode
from parrot.graph.BaseInterpretationNode import Vibe
from parrot.utils.colour import Color


@pytest.fixture
def gl_context():
    """Create a headless OpenGL context for testing"""
    try:
        return mgl.create_context(standalone=True, require=330)
    except Exception as e:
        pytest.skip(f"Cannot create OpenGL context for testing: {e}")


@pytest.fixture
def color_scheme():
    """Create a test color scheme"""
    return ColorScheme(fg=Color("green"), bg=Color("black"), bg_contrast=Color("white"))


@pytest.fixture
def test_frame():
    """Create a test frame with audio data"""
    audio_data = np.sin(np.linspace(0, 4 * np.pi, 100))
    return Frame(
        values={FrameSignal.freq_all: 0.5},
        timeseries={FrameSignal.freq_all.name: audio_data},
    )


class TestOscilloscopeEffectGL:
    """OpenGL-based tests for OscilloscopeEffect"""

    def test_enter_exit_lifecycle(self, gl_context):
        """Test enter/exit lifecycle with OpenGL context"""
        effect = OscilloscopeEffect(width=256, height=256)

        # Test enter
        effect.enter(gl_context)

        # Check that OpenGL resources were created
        assert effect.framebuffer is not None
        assert effect.texture is not None
        assert effect.shader_program is not None
        assert effect.quad_vao is not None
        assert effect.bloom_framebuffer is not None
        assert effect.bloom_texture is not None
        assert effect.blur_program is not None
        assert effect.composite_program is not None

        # Test exit
        effect.exit()

        # Resources should be cleaned up
        assert effect.framebuffer is None
        assert effect.texture is None
        assert effect.shader_program is None
        assert effect.quad_vao is None
        assert effect.bloom_framebuffer is None
        assert effect.bloom_texture is None
        assert effect.blur_program is None
        assert effect.composite_program is None

    def test_shader_compilation(self, gl_context):
        """Test that all shaders compile successfully"""
        effect = OscilloscopeEffect(width=256, height=256)
        effect.enter(gl_context)

        try:
            # Test main shader program
            assert effect.shader_program is not None
            assert effect.shader_program.ctx == gl_context

            # Test blur shader program
            assert effect.blur_program is not None
            assert effect.blur_program.ctx == gl_context

            # Test composite shader program
            assert effect.composite_program is not None
            assert effect.composite_program.ctx == gl_context

        finally:
            effect.exit()

    def test_waveform_texture_creation(self, gl_context, test_frame):
        """Test that waveform texture is created correctly"""
        effect = OscilloscopeEffect(width=256, height=256)
        effect.enter(gl_context)

        try:
            # Update waveform history
            effect._update_waveform_history(test_frame)
            assert len(effect.waveform_history) > 0

            # Test texture binding (this should not crash)
            effect._bind_waveform_texture()

            # Check that texture was created
            assert hasattr(effect, "_waveform_texture")
            assert effect._waveform_texture is not None

        finally:
            effect.exit()

    def test_render_without_crash(self, gl_context, test_frame, color_scheme):
        """Test that render method completes without crashing"""
        effect = OscilloscopeEffect(width=256, height=256)
        effect.enter(gl_context)

        try:
            # This should not crash
            result = effect.render(test_frame, color_scheme, gl_context)

            # Check that we got a framebuffer back
            assert result is not None
            assert isinstance(result, mgl.Framebuffer)
            assert result.width == 256
            assert result.height == 256

        finally:
            effect.exit()

    def test_render_with_empty_frame(self, gl_context, color_scheme):
        """Test render with frame that has no timeseries data"""
        effect = OscilloscopeEffect(width=256, height=256)
        effect.enter(gl_context)

        try:
            # Frame without timeseries data
            empty_frame = Frame(values={FrameSignal.freq_all: 0.5})

            # Should use fallback waveform and not crash
            result = effect.render(empty_frame, color_scheme, gl_context)

            assert result is not None
            assert isinstance(result, mgl.Framebuffer)

        finally:
            effect.exit()

    def test_multiple_renders(self, gl_context, test_frame, color_scheme):
        """Test multiple consecutive renders"""
        effect = OscilloscopeEffect(width=256, height=256)
        effect.enter(gl_context)

        try:
            # Render multiple times
            for i in range(5):
                result = effect.render(test_frame, color_scheme, gl_context)
                assert result is not None
                assert isinstance(result, mgl.Framebuffer)

        finally:
            effect.exit()

    def test_different_audio_signals(self, gl_context, color_scheme):
        """Test with different audio signal types"""
        effect = OscilloscopeEffect(width=256, height=256, signal=FrameSignal.freq_low)
        effect.enter(gl_context)

        try:
            # Test with different signal types
            for signal in [
                FrameSignal.freq_low,
                FrameSignal.freq_high,
                FrameSignal.freq_all,
            ]:
                effect.signal = signal

                # Create frame with this signal type
                audio_data = np.sin(np.linspace(0, 2 * np.pi, 50))
                frame = Frame(
                    values={signal: 0.7},
                    timeseries={signal.name: audio_data},
                )

                result = effect.render(frame, color_scheme, gl_context)
                assert result is not None

        finally:
            effect.exit()

    def test_parameter_changes(self, gl_context, test_frame, color_scheme):
        """Test that parameter changes work correctly"""
        effect = OscilloscopeEffect(width=256, height=256)
        effect.enter(gl_context)

        try:
            # Change parameters
            effect.line_count = 12
            effect.scroll_speed = 5.0
            effect.waveform_scale = 0.8
            effect.bloom_intensity = 2.5

            # Should still render without issues
            result = effect.render(test_frame, color_scheme, gl_context)
            assert result is not None

        finally:
            effect.exit()

    def test_generate_randomization(self, gl_context, test_frame, color_scheme):
        """Test that generate method randomization works with rendering"""
        effect = OscilloscopeEffect(width=256, height=256)
        effect.enter(gl_context)

        try:
            vibe = Vibe(Mode.rave)

            # Generate new parameters multiple times and render
            for _ in range(3):
                effect.generate(vibe)
                result = effect.render(test_frame, color_scheme, gl_context)
                assert result is not None

        finally:
            effect.exit()

    def test_large_waveform_data(self, gl_context, color_scheme):
        """Test with large waveform data arrays"""
        effect = OscilloscopeEffect(width=256, height=256)
        effect.enter(gl_context)

        try:
            # Create large audio data
            large_audio_data = np.sin(np.linspace(0, 10 * np.pi, 1000))
            frame = Frame(
                values={FrameSignal.freq_all: 0.5},
                timeseries={FrameSignal.freq_all.name: large_audio_data},
            )

            result = effect.render(frame, color_scheme, gl_context)
            assert result is not None

            # Check that history was limited
            assert len(effect.waveform_history) <= effect.max_history_length

        finally:
            effect.exit()

    def test_framebuffer_size_consistency(self, gl_context, test_frame, color_scheme):
        """Test that framebuffer sizes are consistent"""
        for width, height in [(128, 128), (512, 256), (1024, 768)]:
            effect = OscilloscopeEffect(width=width, height=height)
            effect.enter(gl_context)

            try:
                result = effect.render(test_frame, color_scheme, gl_context)

                assert result.width == width
                assert result.height == height
                assert effect.framebuffer.width == width
                assert effect.framebuffer.height == height
                assert effect.bloom_framebuffer.width == width
                assert effect.bloom_framebuffer.height == height

            finally:
                effect.exit()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
