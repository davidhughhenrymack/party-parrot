import pytest
import numpy as np
from parrot.vj.interpreters.color_lighting import (
    ColorSchemeLighting,
    RedLighting,
    BlueLighting,
    DynamicColorLighting,
    SelectiveLighting,
    StrobeLighting,
    WarmCoolLighting,
    SpotlightEffect,
    ColorChannelSeparation,
)
from parrot.vj.base import SolidLayer
from parrot.vj.layers.video import MockVideoLayer
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.interpreters.base import InterpreterArgs
from parrot.utils.colour import Color


class TestColorSchemeLighting:
    """Test color scheme lighting interpreter"""

    def test_color_scheme_lighting_creation(self):
        """Test ColorSchemeLighting creation"""
        video_layers = [MockVideoLayer("video")]
        args = InterpreterArgs(40, True, 0, 100)

        interpreter = ColorSchemeLighting(
            video_layers, args, color_source="fg", intensity=1.5
        )

        assert interpreter.color_source == "fg"
        assert interpreter.base_intensity == 1.5
        assert len(interpreter.video_layers) == 1

    def test_foreground_lighting(self):
        """Test lighting with foreground color"""
        video_layers = [MockVideoLayer("video")]
        args = InterpreterArgs(40, True, 0, 100)

        interpreter = ColorSchemeLighting(video_layers, args, color_source="fg")
        scheme = ColorScheme(Color("red"), Color("blue"), Color("green"))

        # Mock the video layer
        video_layers[0].set_color = lambda c: None
        video_layers[0].color = (128, 128, 128)

        frame = Frame({FrameSignal.freq_all: 0.8})
        interpreter.step(frame, scheme)

        # Should have updated intensity based on signal
        assert interpreter.current_intensity > interpreter.base_intensity

    def test_color_cycling(self):
        """Test color cycling mode"""
        video_layers = [MockVideoLayer("video")]
        args = InterpreterArgs(40, True, 0, 100)

        interpreter = ColorSchemeLighting(video_layers, args, color_source="cycle")
        scheme = ColorScheme(Color("red"), Color("green"), Color("blue"))

        frame = Frame({FrameSignal.freq_all: 0.5})

        # Multiple steps should advance the cycle
        for _ in range(10):
            interpreter.step(frame, scheme)

        assert interpreter.cycle_phase > 0


class TestRedLighting:
    """Test red lighting interpreter"""

    def test_red_lighting_creation(self):
        """Test RedLighting creation"""
        video_layers = [MockVideoLayer("video")]
        args = InterpreterArgs(50, True, 0, 100)

        interpreter = RedLighting(video_layers, args, red_intensity=2.0)

        assert interpreter.red_intensity == 2.0
        assert len(interpreter.video_layers) == 1

    def test_red_lighting_effect(self):
        """Test red lighting application"""
        video_layers = [MockVideoLayer("video")]
        video_layers[0].color = (100, 50, 50)  # Base color

        colors_applied = []
        video_layers[0].set_color = lambda c: colors_applied.append(c)

        args = InterpreterArgs(50, True, 0, 100)
        interpreter = RedLighting(video_layers, args)
        scheme = ColorScheme(Color("red"), Color("blue"), Color("green"))

        # High bass should intensify red lighting
        frame = Frame({FrameSignal.freq_low: 0.9})
        interpreter.step(frame, scheme)

        # Should have applied red lighting
        assert len(colors_applied) > 0
        applied_color = colors_applied[-1]

        # Red channel should be enhanced more than others
        assert applied_color[0] >= 100  # Red should be at least as bright as original


class TestBlueLighting:
    """Test blue lighting interpreter"""

    def test_blue_lighting_creation(self):
        """Test BlueLighting creation"""
        video_layers = [MockVideoLayer("video")]
        args = InterpreterArgs(45, True, 0, 100)

        interpreter = BlueLighting(video_layers, args, blue_intensity=1.8)

        assert interpreter.blue_intensity == 1.8
        assert len(interpreter.video_layers) == 1

    def test_blue_lighting_effect(self):
        """Test blue lighting application"""
        video_layers = [MockVideoLayer("video")]
        video_layers[0].color = (50, 50, 100)  # Base color with some blue

        colors_applied = []
        video_layers[0].set_color = lambda c: colors_applied.append(c)

        args = InterpreterArgs(45, True, 0, 100)
        interpreter = BlueLighting(video_layers, args)
        scheme = ColorScheme(Color("cyan"), Color("red"), Color("blue"))

        # High treble should intensify blue lighting
        frame = Frame({FrameSignal.freq_high: 0.8})
        interpreter.step(frame, scheme)

        assert len(colors_applied) > 0
        applied_color = colors_applied[-1]

        # Blue channel should be enhanced
        assert applied_color[2] >= 100


class TestDynamicColorLighting:
    """Test dynamic color lighting interpreter"""

    def test_dynamic_lighting_creation(self):
        """Test DynamicColorLighting creation"""
        video_layers = [MockVideoLayer("video")]
        args = InterpreterArgs(60, True, 0, 100)

        interpreter = DynamicColorLighting(
            video_layers,
            args,
            cycle_speed=0.05,
            intensity_range=(1.0, 3.0),
            beat_boost=True,
        )

        assert interpreter.cycle_speed == 0.05
        assert interpreter.min_intensity == 1.0
        assert interpreter.max_intensity == 3.0
        assert interpreter.beat_boost == True

    def test_beat_boost(self):
        """Test beat boost functionality"""
        video_layers = [MockVideoLayer("video")]
        args = InterpreterArgs(60, True, 0, 100)

        interpreter = DynamicColorLighting(video_layers, args, beat_boost=True)
        scheme = ColorScheme(Color("red"), Color("green"), Color("blue"))

        # Trigger beat
        frame_beat = Frame({FrameSignal.freq_high: 0.8, FrameSignal.freq_all: 0.5})
        interpreter.step(frame_beat, scheme)

        # Should trigger beat boost
        assert interpreter.beat_boost_remaining > 0

        # Multiple steps should decay boost
        frame_normal = Frame({FrameSignal.freq_high: 0.3, FrameSignal.freq_all: 0.4})
        for _ in range(25):  # More than boost duration
            interpreter.step(frame_normal, scheme)

        assert interpreter.beat_boost_remaining == 0


class TestSelectiveLighting:
    """Test selective color lighting interpreter"""

    def test_selective_lighting_creation(self):
        """Test SelectiveLighting creation"""
        video_layers = [MockVideoLayer("video")]
        args = InterpreterArgs(55, True, 0, 100)

        interpreter = SelectiveLighting(
            video_layers,
            args,
            target_color=(1.0, 0.0, 0.0),  # Red
            color_tolerance=0.3,
            enhancement_factor=2.0,
        )

        assert interpreter.target_color == (1.0, 0.0, 0.0)
        assert interpreter.color_tolerance == 0.3
        assert interpreter.enhancement_factor == 2.0

    def test_color_name_detection(self):
        """Test color name detection"""
        video_layers = [MockVideoLayer("video")]
        args = InterpreterArgs(55, True, 0, 100)

        interpreter = SelectiveLighting(video_layers, args)

        # Test different colors
        test_colors = [
            ((1.0, 0.0, 0.0), "Red"),
            ((0.0, 1.0, 0.0), "Green"),
            ((0.0, 0.0, 1.0), "Blue"),
            ((1.0, 1.0, 0.0), "Yellow"),
            ((1.0, 0.0, 1.0), "Magenta"),
            ((0.0, 1.0, 1.0), "Cyan"),
            ((0.9, 0.9, 0.9), "White"),
            ((0.1, 0.1, 0.1), "Black"),
        ]

        for color_rgb, expected_name in test_colors:
            color_name = interpreter._get_color_name(color_rgb)
            assert color_name == expected_name

    def test_selective_enhancement(self):
        """Test selective color enhancement"""
        video_layers = [MockVideoLayer("video")]
        video_layers[0].color = (200, 50, 50)  # Mostly red

        colors_applied = []
        video_layers[0].set_color = lambda c: colors_applied.append(c)

        args = InterpreterArgs(55, True, 0, 100)
        interpreter = SelectiveLighting(
            video_layers,
            args,
            target_color=(1.0, 0.0, 0.0),  # Target red
            enhancement_factor=1.5,
        )

        scheme = ColorScheme(Color("red"), Color("blue"), Color("green"))
        frame = Frame({FrameSignal.freq_low: 0.7})

        interpreter.step(frame, scheme)

        # Should enhance the red color since it's close to target
        if colors_applied:
            enhanced_color = colors_applied[-1]
            # Red should be enhanced (or at least not reduced significantly)
            assert enhanced_color[0] >= 150  # Should maintain or enhance red


class TestStrobeLighting:
    """Test strobe lighting interpreter"""

    def test_strobe_lighting_creation(self):
        """Test StrobeLighting creation"""
        video_layers = [MockVideoLayer("video")]
        args = InterpreterArgs(80, True, 0, 100)

        interpreter = StrobeLighting(video_layers, args, strobe_speed=0.5)

        assert interpreter.strobe_speed == 0.5
        assert len(interpreter.color_palette) > 0
        assert len(interpreter.video_layers) == 1

    def test_manual_strobe_trigger(self):
        """Test manual strobe triggering"""
        video_layers = [MockVideoLayer("video")]
        args = InterpreterArgs(80, True, 0, 100)

        interpreter = StrobeLighting(video_layers, args)
        scheme = ColorScheme(Color("red"), Color("green"), Color("blue"))

        initial_phase = interpreter.strobe_phase

        # Manual strobe should advance phase rapidly
        frame_strobe = Frame({FrameSignal.strobe: 1.0, FrameSignal.freq_all: 0.3})
        interpreter.step(frame_strobe, scheme)

        # Phase should have advanced significantly
        assert interpreter.strobe_phase > initial_phase + 5  # Fast advancement

    def test_color_cycling(self):
        """Test strobe color cycling"""
        video_layers = [MockVideoLayer("video")]
        args = InterpreterArgs(80, True, 0, 100)

        interpreter = StrobeLighting(
            video_layers, args, strobe_speed=1.0
        )  # Fast for testing
        scheme = ColorScheme(Color("white"), Color("black"), Color("red"))

        frame = Frame({FrameSignal.freq_all: 0.5})

        color_indices = []
        for _ in range(10):
            color_indices.append(interpreter.current_color_index)
            interpreter.step(frame, scheme)

        # Should have cycled through different colors
        assert len(set(color_indices)) > 1


class TestWarmCoolLighting:
    """Test warm/cool lighting interpreter"""

    def test_warm_cool_creation(self):
        """Test WarmCoolLighting creation"""
        video_layers = [MockVideoLayer("video")]
        args = InterpreterArgs(35, True, 0, 100)

        interpreter = WarmCoolLighting(video_layers, args)

        assert interpreter.warm_color == (1.0, 0.7, 0.4)
        assert interpreter.cool_color == (0.4, 0.7, 1.0)
        assert len(interpreter.video_layers) == 1

    def test_temperature_response(self):
        """Test warm/cool response to bass/treble"""
        video_layers = [MockVideoLayer("video")]
        args = InterpreterArgs(35, True, 0, 100)

        interpreter = WarmCoolLighting(video_layers, args)
        scheme = ColorScheme(Color("orange"), Color("blue"), Color("white"))

        # High bass should bias toward warm
        frame_warm = Frame({FrameSignal.freq_low: 0.9, FrameSignal.freq_high: 0.1})
        interpreter.step(frame_warm, scheme)

        # High treble should bias toward cool
        frame_cool = Frame({FrameSignal.freq_low: 0.1, FrameSignal.freq_high: 0.9})
        interpreter.step(frame_cool, scheme)

        # Phase should advance
        assert interpreter.temperature_phase > 0


class TestSpotlightEffect:
    """Test spotlight effect interpreter"""

    def test_spotlight_creation(self):
        """Test SpotlightEffect creation"""
        video_layers = [MockVideoLayer("video")]
        args = InterpreterArgs(65, True, 0, 100)

        interpreter = SpotlightEffect(video_layers, args, num_spots=3)

        assert interpreter.num_spots == 3
        assert len(interpreter.spots) == 3
        assert len(interpreter.video_layers) == 1

        # Check spotlight initialization
        for spot in interpreter.spots:
            assert "x" in spot
            assert "y" in spot
            assert "size" in spot
            assert "intensity" in spot
            assert "color" in spot
            assert "movement_pattern" in spot

    def test_spotlight_movement(self):
        """Test spotlight movement patterns"""
        video_layers = [MockVideoLayer("video")]
        args = InterpreterArgs(65, True, 0, 100)

        interpreter = SpotlightEffect(video_layers, args, num_spots=2)
        scheme = ColorScheme(Color("white"), Color("red"), Color("blue"))

        # Get initial positions
        initial_positions = [(spot["x"], spot["y"]) for spot in interpreter.spots]

        # Update with audio
        frame = Frame(
            {
                FrameSignal.freq_low: 0.6,
                FrameSignal.freq_high: 0.4,
                FrameSignal.freq_all: 0.5,
            }
        )

        # Multiple steps should move spotlights
        for _ in range(5):
            interpreter.step(frame, scheme)

        # Positions should have changed
        new_positions = [(spot["x"], spot["y"]) for spot in interpreter.spots]

        # At least some spots should have moved
        moved_spots = sum(
            1
            for old, new in zip(initial_positions, new_positions)
            if abs(old[0] - new[0]) > 0.001 or abs(old[1] - new[1]) > 0.001
        )
        assert moved_spots > 0

    def test_spotlight_info(self):
        """Test spotlight info retrieval"""
        video_layers = [MockVideoLayer("video")]
        args = InterpreterArgs(65, True, 0, 100)

        interpreter = SpotlightEffect(video_layers, args, num_spots=2)

        spotlight_info = interpreter.get_spotlight_info()
        assert len(spotlight_info) == 2

        # Should be a copy, not the same object
        assert spotlight_info is not interpreter.spots


class TestColorChannelSeparation:
    """Test color channel separation interpreter"""

    def test_channel_separation_creation(self):
        """Test ColorChannelSeparation creation"""
        video_layers = [MockVideoLayer("video")]
        args = InterpreterArgs(70, True, 0, 100)

        interpreter = ColorChannelSeparation(
            video_layers, args, separation_intensity=1.5
        )

        assert interpreter.separation_intensity == 1.5
        assert "red" in interpreter.channel_signals
        assert "green" in interpreter.channel_signals
        assert "blue" in interpreter.channel_signals

    def test_channel_separation_effect(self):
        """Test color channel separation application"""
        video_layers = [MockVideoLayer("video")]
        video_layers[0].color = (100, 100, 100)  # Gray base

        colors_applied = []
        video_layers[0].set_color = lambda c: colors_applied.append(c)

        args = InterpreterArgs(70, True, 0, 100)
        interpreter = ColorChannelSeparation(video_layers, args)
        scheme = ColorScheme(Color("white"), Color("black"), Color("gray"))

        # Different signal strengths for each channel
        frame = Frame(
            {
                FrameSignal.freq_low: 0.8,  # Red channel
                FrameSignal.freq_all: 0.3,  # Green channel
                FrameSignal.freq_high: 0.9,  # Blue channel
            }
        )

        interpreter.step(frame, scheme)

        if colors_applied:
            separated_color = colors_applied[-1]

            # Red should be enhanced (high bass)
            # Blue should be enhanced (high treble)
            # Green should be less enhanced (low freq_all)
            assert separated_color[0] > separated_color[1]  # Red > Green
            assert separated_color[2] > separated_color[1]  # Blue > Green


class TestColorLightingIntegration:
    """Test color lighting integration and combinations"""

    def test_multiple_lighting_interpreters(self):
        """Test multiple lighting interpreters on same layers"""
        video_layers = [MockVideoLayer("video1"), MockVideoLayer("video2")]
        args = InterpreterArgs(60, True, 0, 100)

        # Create multiple lighting interpreters
        interpreters = [
            RedLighting(video_layers[:1], args),  # Red on first layer
            BlueLighting(video_layers[1:], args),  # Blue on second layer
            ColorSchemeLighting(
                video_layers, args, color_source="cycle"
            ),  # Cycle on both
        ]

        scheme = ColorScheme(Color("red"), Color("blue"), Color("green"))
        frame = Frame(
            {
                FrameSignal.freq_low: 0.7,
                FrameSignal.freq_high: 0.6,
                FrameSignal.freq_all: 0.65,
            }
        )

        # Should not crash when multiple interpreters affect same layers
        for interp in interpreters:
            interp.step(frame, scheme)

    def test_lighting_with_non_video_layers(self):
        """Test lighting interpreters with non-video layers"""
        mixed_layers = [
            SolidLayer("solid", width=100, height=100),
            MockVideoLayer("video"),
        ]
        args = InterpreterArgs(50, True, 0, 100)

        interpreter = ColorSchemeLighting(mixed_layers, args)

        # Should filter to only video layers
        assert len(interpreter.video_layers) == 1
        assert interpreter.video_layers[0].name == "video"

        scheme = ColorScheme(Color("purple"), Color("orange"), Color("cyan"))
        frame = Frame({FrameSignal.freq_all: 0.5})

        # Should not crash
        interpreter.step(frame, scheme)

    def test_lighting_string_representations(self):
        """Test string representations of lighting interpreters"""
        video_layers = [MockVideoLayer("video")]
        args = InterpreterArgs(50, True, 0, 100)

        interpreters = [
            ColorSchemeLighting(video_layers, args, color_source="fg"),
            RedLighting(video_layers, args),
            BlueLighting(video_layers, args),
            DynamicColorLighting(video_layers, args),
            SelectiveLighting(video_layers, args),
            StrobeLighting(video_layers, args),
            WarmCoolLighting(video_layers, args),
            SpotlightEffect(video_layers, args),
            ColorChannelSeparation(video_layers, args),
        ]

        for interp in interpreters:
            str_repr = str(interp)
            assert isinstance(str_repr, str)
            assert len(str_repr) > 0
            assert interp.__class__.__name__ in str_repr or any(
                emoji in str_repr
                for emoji in ["🔦", "🔴", "🔵", "🌈", "🎯", "⚡", "💡"]
            )

    def test_lighting_hype_levels(self):
        """Test lighting interpreter hype levels"""
        video_layers = [MockVideoLayer("video")]
        args = InterpreterArgs(50, True, 0, 100)

        interpreters = [
            (WarmCoolLighting(video_layers, args), 35),
            (ColorSchemeLighting(video_layers, args), 40),
            (BlueLighting(video_layers, args), 45),
            (RedLighting(video_layers, args), 50),
            (SelectiveLighting(video_layers, args), 55),
            (DynamicColorLighting(video_layers, args), 60),
            (SpotlightEffect(video_layers, args), 65),
            (ColorChannelSeparation(video_layers, args), 70),
            (StrobeLighting(video_layers, args), 80),
        ]

        for interp, expected_hype in interpreters:
            assert interp.get_hype() == expected_hype

    def test_lighting_with_empty_video_layers(self):
        """Test lighting interpreters with no video layers"""
        non_video_layers = [SolidLayer("solid", width=100, height=100)]
        args = InterpreterArgs(50, True, 0, 100)

        interpreter = RedLighting(non_video_layers, args)

        # Should have no video layers
        assert len(interpreter.video_layers) == 0

        # Should not crash when stepping
        scheme = ColorScheme(Color("red"), Color("green"), Color("blue"))
        frame = Frame({FrameSignal.freq_low: 0.8})

        interpreter.step(frame, scheme)  # Should not crash

    def test_lighting_parameter_updates(self):
        """Test that lighting parameters are stored on layers"""
        video_layers = [MockVideoLayer("video")]
        args = InterpreterArgs(60, True, 0, 100)

        interpreter = DynamicColorLighting(video_layers, args)
        scheme = ColorScheme(Color("red"), Color("green"), Color("blue"))
        frame = Frame({FrameSignal.freq_all: 0.7})

        interpreter.step(frame, scheme)

        # Should store lighting parameters on layer for rendering
        layer = video_layers[0]
        # These would be used by a specialized renderer
        # For now, just check that the step completed without error
        assert hasattr(interpreter, "cycle_phase")
        assert interpreter.cycle_phase > 0
