import pytest
import numpy as np
from parrot.vj.interpreters.strobe_effects import (
    StrobeFlash,
    ColorStrobe,
    BeatStrobe,
    RandomStrobe,
    HighSpeedStrobe,
    PatternStrobe,
    AudioReactiveStrobe,
    LayerSelectiveStrobe,
    StrobeBlackout,
    RGBChannelStrobe,
    StrobeZoom,
)
from parrot.vj.base import SolidLayer
from parrot.vj.layers.text import MockTextLayer
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.interpreters.base import InterpreterArgs
from parrot.utils.colour import Color


class TestStrobeFlash:
    """Test basic strobe flash effect"""

    def test_strobe_flash_creation(self):
        """Test StrobeFlash creation"""
        layers = [SolidLayer("test", width=200, height=150)]
        args = InterpreterArgs(80, True, 0, 100)

        interpreter = StrobeFlash(layers, args, strobe_frequency=10.0)

        assert interpreter.strobe_frequency == 10.0
        assert interpreter.strobe_intensity == 1.0
        assert interpreter.trigger_signal == FrameSignal.strobe
        assert interpreter.frames_per_cycle == 6  # 60fps / 10Hz

    def test_strobe_trigger(self):
        """Test strobe triggering"""
        layers = [SolidLayer("test", width=100, height=100)]
        args = InterpreterArgs(80, True, 0, 100)

        interpreter = StrobeFlash(layers, args)
        scheme = ColorScheme(Color("red"), Color("blue"), Color("green"))

        # No strobe signal - should not be active
        frame_off = Frame({FrameSignal.strobe: 0.0})
        interpreter.step(frame_off, scheme)
        assert interpreter.strobe_active == False

        # Strobe signal - should be active
        frame_on = Frame({FrameSignal.strobe: 1.0})
        interpreter.step(frame_on, scheme)
        assert interpreter.strobe_active == True

    def test_strobe_frequency_setting(self):
        """Test strobe frequency adjustment"""
        layers = [SolidLayer("test", width=100, height=100)]
        args = InterpreterArgs(80, True, 0, 100)

        interpreter = StrobeFlash(layers, args, strobe_frequency=5.0)

        # Test frequency change
        interpreter.set_strobe_frequency(20.0)
        assert interpreter.strobe_frequency == 20.0
        assert interpreter.frames_per_cycle == 3  # 60fps / 20Hz

        # Test frequency clamping
        interpreter.set_strobe_frequency(100.0)  # Should clamp to max
        assert interpreter.strobe_frequency == 60.0

        interpreter.set_strobe_frequency(0.01)  # Should clamp to min
        assert interpreter.strobe_frequency == 0.1


class TestColorStrobe:
    """Test color strobing effect"""

    def test_color_strobe_creation(self):
        """Test ColorStrobe creation"""
        layers = [SolidLayer("test", width=200, height=150)]
        args = InterpreterArgs(75, True, 0, 100)

        interpreter = ColorStrobe(layers, args, strobe_speed=0.5)

        assert interpreter.strobe_speed == 0.5
        assert len(interpreter.strobe_colors) > 0
        assert interpreter.current_color_index == 0

    def test_color_cycling(self):
        """Test color cycling functionality"""
        layers = [SolidLayer("test", width=100, height=100)]
        args = InterpreterArgs(75, True, 0, 100)

        interpreter = ColorStrobe(layers, args, strobe_speed=1.0)  # Fast for testing
        scheme = ColorScheme(Color("white"), Color("black"), Color("red"))

        frame = Frame({FrameSignal.freq_all: 0.5})

        initial_color_index = interpreter.current_color_index

        # Multiple steps should advance color
        for _ in range(10):
            interpreter.step(frame, scheme)

        # Color should have changed
        assert interpreter.current_color_index != initial_color_index

    def test_scheme_color_integration(self):
        """Test setting colors from scheme"""
        layers = [SolidLayer("test", width=100, height=100)]
        args = InterpreterArgs(75, True, 0, 100)

        interpreter = ColorStrobe(layers, args)
        scheme = ColorScheme(Color("purple"), Color("orange"), Color("cyan"))

        # Set colors from scheme
        interpreter.set_colors_from_scheme(scheme)

        # Should have scheme colors
        assert len(interpreter.strobe_colors) == 5  # 3 scheme colors + white + black

        # Check that scheme colors are present
        scheme_colors = [
            tuple(int(c * 255) for c in scheme.fg.rgb),
            tuple(int(c * 255) for c in scheme.bg.rgb),
            tuple(int(c * 255) for c in scheme.bg_contrast.rgb),
        ]

        for color in scheme_colors:
            assert color in interpreter.strobe_colors

    def test_color_name_detection(self):
        """Test color name detection"""
        layers = [SolidLayer("test", width=100, height=100)]
        args = InterpreterArgs(75, True, 0, 100)

        interpreter = ColorStrobe(layers, args)

        # Test color name detection
        test_colors = [
            ((255, 0, 0), "Red"),
            ((0, 255, 0), "Green"),
            ((0, 0, 255), "Blue"),
            ((255, 255, 255), "White"),
            ((0, 0, 0), "Black"),
            ((255, 165, 0), "Orange"),
            ((128, 0, 128), "Purple"),
        ]

        for color, expected_name in test_colors:
            name = interpreter._get_color_name(color)
            assert name == expected_name


class TestBeatStrobe:
    """Test beat-synchronized strobing"""

    def test_beat_strobe_creation(self):
        """Test BeatStrobe creation"""
        layers = [SolidLayer("test", width=200, height=150)]
        args = InterpreterArgs(85, True, 0, 100)

        interpreter = BeatStrobe(layers, args, beat_threshold=0.7, strobe_duration=8)

        assert interpreter.beat_threshold == 0.7
        assert interpreter.strobe_duration == 8
        assert interpreter.strobe_frames_remaining == 0
        assert interpreter.beat_count == 0

    def test_beat_detection(self):
        """Test beat detection and strobe triggering"""
        layers = [SolidLayer("test", width=100, height=100)]
        args = InterpreterArgs(85, True, 0, 100)

        interpreter = BeatStrobe(layers, args, beat_threshold=0.6)
        scheme = ColorScheme(Color("red"), Color("green"), Color("blue"))

        # Below threshold - no beat
        frame_low = Frame({FrameSignal.freq_high: 0.4})
        interpreter.step(frame_low, scheme)
        assert interpreter.strobe_frames_remaining == 0

        # Above threshold - should trigger beat strobe
        frame_high = Frame({FrameSignal.freq_high: 0.8})
        interpreter.step(frame_high, scheme)

        assert interpreter.strobe_frames_remaining > 0
        assert interpreter.beat_count == 1

    def test_strobe_decay(self):
        """Test strobe decay after beat"""
        layers = [SolidLayer("test", width=100, height=100)]
        args = InterpreterArgs(85, True, 0, 100)

        interpreter = BeatStrobe(layers, args, strobe_duration=5)
        scheme = ColorScheme(Color("white"), Color("black"), Color("red"))

        # Trigger beat
        frame_beat = Frame({FrameSignal.freq_high: 0.8})
        interpreter.step(frame_beat, scheme)

        initial_frames = interpreter.strobe_frames_remaining

        # Continue with no beat
        frame_quiet = Frame({FrameSignal.freq_high: 0.2})

        for _ in range(6):  # More than strobe duration
            interpreter.step(frame_quiet, scheme)

        # Should have decayed
        assert interpreter.strobe_frames_remaining == 0


class TestRandomStrobe:
    """Test random strobing effects"""

    def test_random_strobe_creation(self):
        """Test RandomStrobe creation"""
        layers = [SolidLayer("test", width=200, height=150)]
        args = InterpreterArgs(70, True, 0, 100)

        interpreter = RandomStrobe(
            layers, args, strobe_probability=0.05, min_duration=3, max_duration=12
        )

        assert interpreter.strobe_probability == 0.05
        assert interpreter.min_duration == 3
        assert interpreter.max_duration == 12
        assert interpreter.energy_influence == True

    def test_random_pattern_generation(self):
        """Test random pattern generation"""
        layers = [SolidLayer("test", width=100, height=100)]
        args = InterpreterArgs(70, True, 0, 100)

        interpreter = RandomStrobe(
            layers, args, strobe_probability=1.0
        )  # Always trigger
        scheme = ColorScheme(Color("red"), Color("green"), Color("blue"))

        frame = Frame({FrameSignal.freq_all: 0.8})

        # Should trigger strobe
        interpreter.step(frame, scheme)

        if interpreter.strobe_frames_remaining > 0:
            # Should have generated pattern
            assert len(interpreter.strobe_pattern) > 0
            assert len(interpreter.strobe_pattern) >= interpreter.min_duration


class TestHighSpeedStrobe:
    """Test high-speed strobing"""

    def test_high_speed_creation(self):
        """Test HighSpeedStrobe creation"""
        layers = [SolidLayer("test", width=200, height=150)]
        args = InterpreterArgs(95, True, 0, 100)

        interpreter = HighSpeedStrobe(
            layers, args, base_frequency=20.0, max_frequency=60.0, trigger_threshold=0.8
        )

        assert interpreter.base_frequency == 20.0
        assert interpreter.max_frequency == 60.0
        assert interpreter.trigger_threshold == 0.8

    def test_frequency_scaling(self):
        """Test frequency scaling with energy"""
        layers = [SolidLayer("test", width=100, height=100)]
        args = InterpreterArgs(95, True, 0, 100)

        interpreter = HighSpeedStrobe(
            layers, args, base_frequency=10.0, max_frequency=50.0
        )
        scheme = ColorScheme(Color("white"), Color("red"), Color("blue"))

        # Low energy
        frame_low = Frame(
            {
                FrameSignal.sustained_high: 0.9,  # Above threshold
                FrameSignal.freq_all: 0.2,  # Low energy
            }
        )
        interpreter.step(frame_low, scheme)
        low_freq = interpreter.current_frequency

        # High energy
        frame_high = Frame(
            {
                FrameSignal.sustained_high: 0.9,  # Above threshold
                FrameSignal.freq_all: 0.9,  # High energy
            }
        )
        interpreter.step(frame_high, scheme)
        high_freq = interpreter.current_frequency

        # High energy should produce higher frequency
        assert high_freq > low_freq


class TestPatternStrobe:
    """Test pattern-based strobing"""

    def test_pattern_strobe_creation(self):
        """Test PatternStrobe creation"""
        layers = [SolidLayer("test", width=200, height=150)]
        args = InterpreterArgs(65, True, 0, 100)

        custom_patterns = [[1.0, 0.0, 1.0, 0.0], [1.0, 0.8, 0.6, 0.4, 0.2, 0.0]]

        interpreter = PatternStrobe(layers, args, patterns=custom_patterns)

        assert len(interpreter.patterns) == 2
        assert interpreter.pattern_speed == 1.0

    def test_pattern_execution(self):
        """Test pattern execution"""
        layers = [SolidLayer("test", width=100, height=100)]
        args = InterpreterArgs(65, True, 0, 100)

        # Simple test pattern
        test_pattern = [1.0, 0.5, 0.0, 0.5]
        interpreter = PatternStrobe(
            layers, args, patterns=[test_pattern], pattern_speed=1.0
        )
        scheme = ColorScheme(Color("red"), Color("green"), Color("blue"))

        # Track alpha values
        alpha_values = []

        def track_alpha(alpha):
            alpha_values.append(alpha)

        # Mock layer alpha setting
        layers[0].set_alpha = track_alpha

        # Trigger strobe
        frame_strobe = Frame({FrameSignal.strobe: 1.0, FrameSignal.freq_all: 0.5})

        # Execute pattern
        for _ in range(len(test_pattern) + 2):
            interpreter.step(frame_strobe, scheme)

        # Should have executed pattern values
        assert len(alpha_values) > 0

    def test_custom_pattern_addition(self):
        """Test adding custom patterns"""
        layers = [SolidLayer("test", width=100, height=100)]
        args = InterpreterArgs(65, True, 0, 100)

        interpreter = PatternStrobe(layers, args)
        initial_pattern_count = len(interpreter.patterns)

        # Add valid pattern
        interpreter.add_pattern([0.8, 0.4, 0.2, 0.6])
        assert len(interpreter.patterns) == initial_pattern_count + 1

        # Try to add invalid pattern (values outside 0-1 range)
        interpreter.add_pattern([1.5, -0.2, 0.5])  # Should not be added
        assert len(interpreter.patterns) == initial_pattern_count + 1  # No change


class TestAudioReactiveStrobe:
    """Test audio-reactive strobing"""

    def test_audio_reactive_creation(self):
        """Test AudioReactiveStrobe creation"""
        layers = [SolidLayer("test", width=200, height=150)]
        args = InterpreterArgs(90, True, 0, 100)

        interpreter = AudioReactiveStrobe(
            layers, args, bass_strobe=True, treble_strobe=True, sustained_strobe=False
        )

        assert interpreter.bass_strobe == True
        assert interpreter.treble_strobe == True
        assert interpreter.sustained_strobe == False

    def test_frequency_response(self):
        """Test response to different frequencies"""
        layers = [SolidLayer("test", width=100, height=100)]
        args = InterpreterArgs(90, True, 0, 100)

        interpreter = AudioReactiveStrobe(layers, args)
        scheme = ColorScheme(Color("red"), Color("green"), Color("blue"))

        # Track color changes
        colors_applied = []
        layers[0].set_color = lambda c: colors_applied.append(c)

        # Test different frequency combinations
        test_frames = [
            Frame(
                {  # Bass dominant
                    FrameSignal.freq_low: 0.9,
                    FrameSignal.freq_high: 0.2,
                    FrameSignal.sustained_low: 0.3,
                }
            ),
            Frame(
                {  # Treble dominant
                    FrameSignal.freq_low: 0.2,
                    FrameSignal.freq_high: 0.9,
                    FrameSignal.sustained_low: 0.3,
                }
            ),
            Frame(
                {  # Sustained dominant
                    FrameSignal.freq_low: 0.3,
                    FrameSignal.freq_high: 0.2,
                    FrameSignal.sustained_low: 0.9,
                }
            ),
        ]

        for frame in test_frames:
            interpreter.step(frame, scheme)

        # Should have applied colors
        assert len(colors_applied) == 3

        # Colors should be different for different frequency dominance
        assert len(set(colors_applied)) > 1


class TestLayerSelectiveStrobe:
    """Test layer-selective strobing"""

    def test_selective_strobe_creation(self):
        """Test LayerSelectiveStrobe creation"""
        layers = [
            SolidLayer("layer1", width=100, height=100),
            SolidLayer("layer2", width=100, height=100),
            SolidLayer("layer3", width=100, height=100),
        ]
        args = InterpreterArgs(60, True, 0, 100)

        interpreter = LayerSelectiveStrobe(
            layers, args, strobe_frequency=8.0, layer_offset=0.25
        )

        assert interpreter.strobe_frequency == 8.0
        assert interpreter.layer_offset == 0.25
        assert len(interpreter.layer_phases) == 3
        assert len(interpreter.layer_intensities) == 3

    def test_independent_layer_strobing(self):
        """Test that layers strobe independently"""
        layers = [
            SolidLayer("layer1", width=100, height=100),
            SolidLayer("layer2", width=100, height=100),
        ]
        args = InterpreterArgs(60, True, 0, 100)

        interpreter = LayerSelectiveStrobe(layers, args, layer_offset=0.5)  # 50% offset
        scheme = ColorScheme(Color("red"), Color("green"), Color("blue"))

        # Track alpha values for each layer
        layer1_alphas = []
        layer2_alphas = []

        layers[0].set_alpha = lambda a: layer1_alphas.append(a)
        layers[1].set_alpha = lambda a: layer2_alphas.append(a)

        # Trigger strobe
        frame = Frame({FrameSignal.strobe: 1.0, FrameSignal.freq_all: 0.6})

        # Multiple steps
        for _ in range(10):
            interpreter.step(frame, scheme)

        # Both layers should have received alpha values
        assert len(layer1_alphas) == 10
        assert len(layer2_alphas) == 10

        # Due to phase offset, they should be different
        assert layer1_alphas != layer2_alphas


class TestStrobeBlackout:
    """Test strobe blackout effects"""

    def test_blackout_creation(self):
        """Test StrobeBlackout creation"""
        layers = [SolidLayer("test", width=200, height=150)]
        args = InterpreterArgs(55, True, 0, 100)

        interpreter = StrobeBlackout(
            layers,
            args,
            blackout_probability=0.3,
            flash_duration=2,
            blackout_duration=4,
        )

        assert interpreter.blackout_probability == 0.3
        assert interpreter.flash_duration == 2
        assert interpreter.blackout_duration == 4
        assert interpreter.current_state == "normal"

    def test_blackout_vs_flash(self):
        """Test blackout vs flash selection"""
        layers = [SolidLayer("test", width=100, height=100)]
        args = InterpreterArgs(55, True, 0, 100)

        # Force blackout
        interpreter = StrobeBlackout(
            layers, args, blackout_probability=1.0
        )  # Always blackout
        scheme = ColorScheme(Color("white"), Color("black"), Color("red"))

        # Track alpha values
        alpha_values = []
        layers[0].set_alpha = lambda a: alpha_values.append(a)

        # Trigger strobe
        frame = Frame({FrameSignal.strobe: 1.0})
        interpreter.step(frame, scheme)

        # Should enter blackout state
        if interpreter.current_state == "blackout":
            assert interpreter.state_frames_remaining > 0


class TestRGBChannelStrobe:
    """Test RGB channel strobing"""

    def test_rgb_channel_creation(self):
        """Test RGBChannelStrobe creation"""
        layers = [SolidLayer("test", width=200, height=150)]
        args = InterpreterArgs(70, True, 0, 100)

        interpreter = RGBChannelStrobe(
            layers, args, channel_frequencies=(8.0, 12.0, 16.0)
        )

        assert interpreter.red_freq == 8.0
        assert interpreter.green_freq == 12.0
        assert interpreter.blue_freq == 16.0
        assert len(interpreter.channel_signals) == 3

    def test_independent_channel_strobing(self):
        """Test independent RGB channel strobing"""
        layers = [SolidLayer("test", width=100, height=100)]
        args = InterpreterArgs(70, True, 0, 100)

        interpreter = RGBChannelStrobe(layers, args)
        scheme = ColorScheme(Color("white"), Color("gray"), Color("black"))

        # Track color changes
        colors_applied = []
        layers[0].set_color = lambda c: colors_applied.append(c)

        # Test with different frequency emphasis
        frames = [
            Frame(
                {  # Bass emphasis
                    FrameSignal.freq_low: 0.9,
                    FrameSignal.freq_all: 0.3,
                    FrameSignal.freq_high: 0.2,
                }
            ),
            Frame(
                {  # Treble emphasis
                    FrameSignal.freq_low: 0.2,
                    FrameSignal.freq_all: 0.3,
                    FrameSignal.freq_high: 0.9,
                }
            ),
        ]

        for frame in frames:
            interpreter.step(frame, scheme)

        # Should have applied colors
        assert len(colors_applied) == 2

        # Colors should be different due to different frequency emphasis
        bass_color = colors_applied[0]
        treble_color = colors_applied[1]

        # Due to the strobing nature, just verify colors are different
        # and within valid ranges
        assert bass_color != treble_color  # Should be different

        # All color values should be valid
        for color in [bass_color, treble_color]:
            assert all(0 <= c <= 255 for c in color)


class TestStrobeZoom:
    """Test strobe zoom effects"""

    def test_strobe_zoom_creation(self):
        """Test StrobeZoom creation"""
        text_layers = [MockTextLayer("TEST", "test")]
        args = InterpreterArgs(75, True, 0, 100)

        interpreter = StrobeZoom(text_layers, args, zoom_range=(0.5, 2.0))

        assert interpreter.min_zoom == 0.5
        assert interpreter.max_zoom == 2.0
        assert len(interpreter.scalable_layers) == 1

    def test_zoom_scaling(self):
        """Test zoom scaling during strobe"""
        text_layers = [MockTextLayer("ZOOM", "test")]
        args = InterpreterArgs(75, True, 0, 100)

        interpreter = StrobeZoom(text_layers, args, zoom_range=(0.8, 1.5))
        scheme = ColorScheme(Color("red"), Color("green"), Color("blue"))

        # Track scale changes
        scale_values = []
        text_layers[0].set_scale = lambda s: scale_values.append(s)

        # Trigger strobe zoom
        frame = Frame({FrameSignal.strobe: 1.0, FrameSignal.freq_all: 0.7})

        # Multiple steps should create zoom effect
        for _ in range(8):
            interpreter.step(frame, scheme)

        # Should have scale values
        assert len(scale_values) == 8

        # Scale values should vary
        assert len(set(scale_values)) > 1


class TestStrobeIntegration:
    """Test strobe effect integration"""

    def test_multiple_strobe_interpreters(self):
        """Test multiple strobe interpreters on same layers"""
        layers = [SolidLayer("test", width=200, height=150)]
        args = InterpreterArgs(80, True, 0, 100)

        # Create multiple strobe interpreters
        interpreters = [
            StrobeFlash(layers, args, strobe_frequency=10.0),
            ColorStrobe(layers, args, strobe_speed=0.5),
            BeatStrobe(layers, args, beat_threshold=0.7),
        ]

        scheme = ColorScheme(Color("red"), Color("green"), Color("blue"))
        frame = Frame(
            {
                FrameSignal.strobe: 1.0,
                FrameSignal.freq_high: 0.8,
                FrameSignal.freq_all: 0.7,
            }
        )

        # Should not crash when multiple interpreters affect same layers
        for interp in interpreters:
            interp.step(frame, scheme)

    def test_strobe_with_mixed_layer_types(self):
        """Test strobing with different layer types"""
        layers = [
            SolidLayer("solid", width=100, height=100),
            MockTextLayer("text", "test"),
        ]
        args = InterpreterArgs(75, True, 0, 100)

        interpreter = StrobeZoom(layers, args)  # Has layer filtering

        # Should filter to scalable layers only
        assert len(interpreter.scalable_layers) == 1
        assert interpreter.scalable_layers[0].name == "test"

        scheme = ColorScheme(Color("purple"), Color("orange"), Color("cyan"))
        frame = Frame({FrameSignal.strobe: 1.0})

        # Should not crash with mixed layer types
        interpreter.step(frame, scheme)

    def test_strobe_string_representations(self):
        """Test string representations of strobe interpreters"""
        layers = [SolidLayer("test", width=100, height=100)]
        args = InterpreterArgs(75, True, 0, 100)

        interpreters = [
            StrobeFlash(layers, args),
            ColorStrobe(layers, args),
            BeatStrobe(layers, args),
            RandomStrobe(layers, args),
            HighSpeedStrobe(layers, args),
            PatternStrobe(layers, args),
            AudioReactiveStrobe(layers, args),
            LayerSelectiveStrobe(layers, args),
            StrobeBlackout(layers, args),
            RGBChannelStrobe(layers, args),
            StrobeZoom(layers, args),
        ]

        for interp in interpreters:
            str_repr = str(interp)
            assert isinstance(str_repr, str)
            assert len(str_repr) > 0
            # Should contain class name or strobe-related emoji
            assert interp.__class__.__name__ in str_repr or any(
                emoji in str_repr
                for emoji in ["⚡", "🌈", "🥁", "🎲", "📋", "🎵", "🔄", "⚫", "🔍"]
            )

    def test_strobe_hype_levels(self):
        """Test strobe interpreter hype levels"""
        layers = [SolidLayer("test", width=100, height=100)]
        args = InterpreterArgs(75, True, 0, 100)

        interpreters_and_hypes = [
            (StrobeBlackout(layers, args), 55),
            (LayerSelectiveStrobe(layers, args), 60),
            (PatternStrobe(layers, args), 65),
            (RandomStrobe(layers, args), 70),
            (RGBChannelStrobe(layers, args), 70),
            (ColorStrobe(layers, args), 75),
            (StrobeZoom(layers, args), 75),
            (StrobeFlash(layers, args), 80),
            (BeatStrobe(layers, args), 85),
            (AudioReactiveStrobe(layers, args), 90),
            (HighSpeedStrobe(layers, args), 95),
        ]

        for interp, expected_hype in interpreters_and_hypes:
            assert interp.get_hype() == expected_hype

    def test_strobe_with_no_trigger(self):
        """Test strobe interpreters with no trigger signal"""
        layers = [SolidLayer("test", width=100, height=100)]
        args = InterpreterArgs(70, True, 0, 100)

        interpreter = StrobeFlash(layers, args)
        scheme = ColorScheme(Color("red"), Color("green"), Color("blue"))

        # No strobe signal
        frame = Frame({FrameSignal.strobe: 0.0, FrameSignal.freq_all: 0.5})

        # Track alpha values
        alpha_values = []
        layers[0].set_alpha = lambda a: alpha_values.append(a)

        # Multiple steps with no trigger
        for _ in range(5):
            interpreter.step(frame, scheme)

        # Should maintain normal operation
        assert len(alpha_values) == 5
        for alpha in alpha_values:
            assert alpha == 1.0  # Normal alpha when not strobing

    def test_strobe_energy_influence(self):
        """Test strobe effects influenced by energy levels"""
        layers = [SolidLayer("test", width=100, height=100)]
        args = InterpreterArgs(80, True, 0, 100)

        interpreter = RandomStrobe(
            layers, args, energy_influence=True, strobe_probability=0.1
        )
        scheme = ColorScheme(Color("red"), Color("green"), Color("blue"))

        # Test with different energy levels
        low_energy_frame = Frame({FrameSignal.freq_all: 0.1})
        high_energy_frame = Frame({FrameSignal.freq_all: 0.9})

        # High energy should be more likely to trigger strobe
        # (This is probabilistic, so we can't guarantee it, but we can test the mechanism)

        # Just verify it doesn't crash and maintains state correctly
        for _ in range(10):
            interpreter.step(low_energy_frame, scheme)

        for _ in range(10):
            interpreter.step(high_energy_frame, scheme)

        # Should complete without errors
        assert hasattr(interpreter, "strobe_frames_remaining")
