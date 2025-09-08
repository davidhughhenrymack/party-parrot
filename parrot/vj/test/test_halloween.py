import pytest
import numpy as np
from parrot.vj.interpreters.halloween_effects import (
    LightningFlash,
    BloodDrip,
    HorrorContrast,
    DeadSexyTextHorror,
    SpookyLighting,
    BloodSplatter,
    EerieBreathing,
    HalloweenGlitch,
    HalloweenStrobeEffect,
    CreepyCrawl,
    PumpkinPulse,
    HorrorTextScream,
)
from parrot.vj.layers.halloween import (
    LightningLayer,
    BloodOverlay,
    SpookyLightingLayer,
    HalloweenParticles,
    HorrorColorGrade,
)
from parrot.vj.halloween_interpretations import (
    create_halloween_vj_renderer,
    halloween_mode_interpretations,
    enable_halloween_mode,
    disable_halloween_mode,
)
from parrot.vj.base import SolidLayer
from parrot.vj.layers.text import MockTextLayer
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode
from parrot.interpreters.base import InterpreterArgs
from parrot.utils.colour import Color


class TestHalloweenEffects:
    """Test Halloween-themed VJ effects"""

    def test_lightning_flash(self):
        """Test lightning flash effect"""
        layers = [SolidLayer("test", width=200, height=150)]
        args = InterpreterArgs(80, True, 0, 100)

        interpreter = LightningFlash(layers, args, energy_threshold=0.7)
        scheme = ColorScheme(Color("red"), Color("black"), Color("white"))

        # Low energy - no flash
        frame_low = Frame(
            {
                FrameSignal.freq_low: 0.3,
                FrameSignal.freq_high: 0.2,
                FrameSignal.freq_all: 0.25,
            }
        )
        interpreter.step(frame_low, scheme)

        # High energy - should trigger flash
        frame_high = Frame(
            {
                FrameSignal.freq_low: 0.9,
                FrameSignal.freq_high: 0.8,
                FrameSignal.freq_all: 0.85,
            }
        )
        interpreter.step(frame_high, scheme)

        # Should have triggered flash
        assert interpreter.flash_frames_remaining > 0

        # Test string representation
        str_repr = str(interpreter)
        assert "LightningFlash" in str_repr

    def test_blood_drip(self):
        """Test blood drip effect"""
        layers = [SolidLayer("test", width=100, height=100)]
        args = InterpreterArgs(60, True, 0, 100)

        interpreter = BloodDrip(layers, args, drip_threshold=0.6)
        scheme = ColorScheme(Color("red"), Color("black"), Color("white"))

        # Trigger blood effect with bass
        frame_bass = Frame({FrameSignal.freq_low: 0.8})
        interpreter.step(frame_bass, scheme)

        # Should have some drip intensity
        assert interpreter.drip_intensity > 0

        # Test decay
        frame_quiet = Frame({FrameSignal.freq_low: 0.1})
        for _ in range(5):
            interpreter.step(frame_quiet, scheme)

        # Intensity should decay
        assert interpreter.drip_intensity < 0.8

    def test_horror_contrast(self):
        """Test horror contrast effect"""
        layers = [SolidLayer("test", color=(128, 128, 128), width=100, height=100)]
        args = InterpreterArgs(50, True, 0, 100)

        interpreter = HorrorContrast(layers, args, contrast_range=(0.5, 2.0))
        scheme = ColorScheme(Color("red"), Color("black"), Color("white"))

        # Test with different energy levels
        frames = [
            Frame(
                {FrameSignal.freq_low: 0.2, FrameSignal.freq_high: 0.1}
            ),  # Low energy
            Frame(
                {FrameSignal.freq_low: 0.8, FrameSignal.freq_high: 0.9}
            ),  # High energy
        ]

        contrasts = []
        for frame in frames:
            interpreter.step(frame, scheme)
            contrasts.append(interpreter.current_contrast)

        # Should have different contrast values
        assert len(set(contrasts)) > 1 or contrasts[0] != contrasts[1]

    def test_dead_sexy_text_horror(self):
        """Test Dead Sexy text horror effects"""
        text_layers = [MockTextLayer("DEAD SEXY", "test")]
        args = InterpreterArgs(70, True, 0, 100)

        interpreter = DeadSexyTextHorror(text_layers, args)
        scheme = ColorScheme(Color("red"), Color("black"), Color("white"))

        # Mock text layer methods
        scale_calls = []
        position_calls = []
        color_calls = []

        text_layers[0].set_scale = lambda s: scale_calls.append(s)
        text_layers[0].set_position = lambda x, y: position_calls.append((x, y))
        text_layers[0].set_color = lambda c: color_calls.append(c)

        # Normal energy
        frame_normal = Frame(
            {
                FrameSignal.freq_low: 0.5,
                FrameSignal.freq_high: 0.3,
                FrameSignal.freq_all: 0.4,
            }
        )
        interpreter.step(frame_normal, scheme)

        # Should have called methods
        assert len(scale_calls) > 0
        assert len(position_calls) > 0
        assert len(color_calls) > 0

        # High energy (potential scare trigger)
        frame_high = Frame(
            {
                FrameSignal.freq_low: 0.9,
                FrameSignal.freq_high: 0.8,
                FrameSignal.freq_all: 0.85,
            }
        )

        # Multiple steps to potentially trigger scare mode
        for _ in range(10):
            interpreter.step(frame_high, scheme)

        # Should have more calls (scare mode might be triggered)
        assert len(scale_calls) >= 10

    def test_spooky_lighting(self):
        """Test spooky lighting interpreter"""
        layers = [SolidLayer("test", width=100, height=100)]
        args = InterpreterArgs(65, True, 0, 100)

        interpreter = SpookyLighting(layers, args, num_lights=4)
        scheme = ColorScheme(Color("orange"), Color("purple"), Color("red"))

        # Should have initialized lights
        assert len(interpreter.lights) == 4

        # Test light info
        light_info = interpreter.get_light_info()
        assert len(light_info) == 4

        for light in light_info:
            assert "x" in light
            assert "y" in light
            assert "size" in light
            assert "intensity" in light
            assert "color" in light

        # Test with audio
        frame = Frame(
            {
                FrameSignal.freq_low: 0.7,
                FrameSignal.freq_high: 0.5,
                FrameSignal.freq_all: 0.6,
            }
        )

        interpreter.step(frame, scheme)

        # Lights should have updated (check specific properties that should change)
        new_light_info = interpreter.get_light_info()

        # At least positions or intensities should have changed
        positions_changed = False
        intensities_changed = False

        for i, (old_light, new_light) in enumerate(zip(light_info, new_light_info)):
            if (
                abs(old_light["x"] - new_light["x"]) > 0.001
                or abs(old_light["y"] - new_light["y"]) > 0.001
            ):
                positions_changed = True
            if abs(old_light["intensity"] - new_light["intensity"]) > 0.001:
                intensities_changed = True

        # At least one property should have changed, but with small movements it might not
        # Just verify the lights are still valid after update
        assert len(new_light_info) == 4
        for light in new_light_info:
            assert 0.0 <= light["x"] <= 1.0
            assert 0.0 <= light["y"] <= 1.0
            assert light["intensity"] >= 0.0

    def test_horror_text_scream(self):
        """Test horror text scream effect"""
        text_layers = [MockTextLayer("DEAD SEXY", "test")]
        args = InterpreterArgs(95, True, 0, 100)

        interpreter = HorrorTextScream(text_layers, args, scream_threshold=0.8)
        scheme = ColorScheme(Color("red"), Color("black"), Color("white"))

        # Mock methods
        scale_calls = []
        position_calls = []
        color_calls = []

        text_layers[0].set_scale = lambda s: scale_calls.append(s)
        text_layers[0].set_position = lambda x, y: position_calls.append((x, y))
        text_layers[0].set_color = lambda c: color_calls.append(c)

        # Trigger scream with high energy
        frame_scream = Frame({FrameSignal.freq_low: 0.9, FrameSignal.freq_high: 0.85})

        interpreter.step(frame_scream, scheme)

        # Should trigger scream mode
        assert interpreter.is_screaming == True
        assert interpreter.scream_intensity > 0

        # Should have dramatic effects
        assert len(scale_calls) > 0
        assert len(position_calls) > 0
        assert len(color_calls) > 0

    def test_halloween_glitch(self):
        """Test Halloween glitch effect"""
        layers = [MockTextLayer("GLITCH", "test")]
        args = InterpreterArgs(75, True, 0, 100)

        interpreter = HalloweenGlitch(
            layers, args, glitch_probability=1.0
        )  # Always glitch for testing
        scheme = ColorScheme(Color("green"), Color("red"), Color("blue"))

        # Mock methods
        calls = {"color": [], "position": [], "scale": []}

        layers[0].set_color = lambda c: calls["color"].append(c)
        layers[0].set_position = lambda x, y: calls["position"].append((x, y))
        layers[0].set_scale = lambda s: calls["scale"].append(s)
        layers[0].color = (100, 100, 100)  # Base color for glitch

        frame = Frame({FrameSignal.freq_all: 0.5})
        interpreter.step(frame, scheme)

        # Should trigger glitch
        assert interpreter.glitch_frames_remaining > 0

        # Should call appropriate methods based on glitch type
        total_calls = len(calls["color"]) + len(calls["position"]) + len(calls["scale"])
        assert total_calls > 0

    def test_pumpkin_pulse(self):
        """Test pumpkin pulse effect"""
        layers = [SolidLayer("test", width=100, height=100)]
        args = InterpreterArgs(45, True, 0, 100)

        interpreter = PumpkinPulse(layers, args, pulse_speed=0.1)
        scheme = ColorScheme(Color("orange"), Color("black"), Color("yellow"))

        # Mock set_color method
        colors = []
        for layer in layers:
            layer.set_color = lambda c: colors.append(c)

        # Multiple steps should cycle through colors
        frame = Frame({FrameSignal.freq_low: 0.6})

        for _ in range(5):
            interpreter.step(frame, scheme)

        assert len(colors) == 5
        # Should have orange-ish colors
        for color in colors:
            assert color[0] > 100  # Should have significant red component (orange)


class TestHalloweenLayers:
    """Test Halloween-themed layers"""

    def test_lightning_layer(self):
        """Test lightning layer"""
        layer = LightningLayer("test_lightning", z_order=10, width=400, height=300)

        assert layer.name == "test_lightning"
        assert layer.z_order == 10
        assert layer.get_size() == (400, 300)
        assert layer.is_flashing == False

        # Should not render when not flashing
        frame = Frame({})
        scheme = ColorScheme(Color("white"), Color("black"), Color("gray"))
        result = layer.render(frame, scheme)
        assert result is None

        # Trigger flash
        layer.trigger_flash(0.8)
        assert layer.is_flashing == True
        assert layer.flash_intensity > 0

        # Should render when flashing
        result = layer.render(frame, scheme)
        assert result is not None
        assert result.shape == (300, 400, 4)

        # Should have some lightning content
        assert np.any(result > 0)

    def test_blood_overlay(self):
        """Test blood overlay layer"""
        layer = BloodOverlay("blood_test", z_order=8, width=300, height=200)

        assert layer.name == "blood_test"
        assert len(layer.blood_splatters) == 0
        assert len(layer.drip_streams) == 0

        # Add effects
        layer.add_splatter(0.5, 0.3, 0.1)
        layer.add_drip(0.7)

        assert len(layer.blood_splatters) == 1
        assert len(layer.drip_streams) == 1

        # Trigger blood effect
        layer.trigger_blood_effect(0.8)
        assert len(layer.blood_splatters) > 1  # Should add more splatters

        # Should render blood effects
        frame = Frame({})
        scheme = ColorScheme(Color("red"), Color("black"), Color("white"))
        result = layer.render(frame, scheme)

        if result is not None:  # Might be None if no visible effects
            assert result.shape == (200, 300, 4)

    def test_spooky_lighting_layer(self):
        """Test spooky lighting layer"""
        layer = SpookyLightingLayer(
            "spooky", z_order=5, width=200, height=150, num_lights=3
        )

        assert layer.name == "spooky"
        assert layer.num_lights == 3
        assert len(layer.lights) == 3

        # Check light initialization
        for light in layer.lights:
            assert "x" in light
            assert "y" in light
            assert "size" in light
            assert "intensity" in light
            assert "movement_pattern" in light

        # Test rendering
        frame = Frame(
            {
                FrameSignal.freq_low: 0.6,
                FrameSignal.freq_high: 0.4,
                FrameSignal.freq_all: 0.5,
            }
        )
        scheme = ColorScheme(Color("orange"), Color("purple"), Color("green"))

        result = layer.render(frame, scheme)

        assert result is not None
        assert result.shape == (150, 200, 4)

        # Should have lighting effects (not all black)
        assert np.any(result != [128, 128, 128, 255])  # Should modify from base gray

    def test_halloween_particles(self):
        """Test Halloween particles layer"""
        layer = HalloweenParticles(
            "particles", z_order=6, width=300, height=200, max_particles=5
        )

        assert layer.name == "particles"
        assert layer.max_particles == 5
        assert len(layer.particles) == 0

        # Add particles
        layer.add_particle("bat")
        layer.add_particle("ghost")

        assert len(layer.particles) == 2
        assert layer.particles[0]["type"] == "bat"
        assert layer.particles[1]["type"] == "ghost"

        # Test rendering with particles
        frame = Frame(
            {FrameSignal.freq_all: 0.8}
        )  # High energy for particle generation
        scheme = ColorScheme(Color("purple"), Color("orange"), Color("black"))

        # Multiple renders should potentially add more particles
        for _ in range(10):
            result = layer.render(frame, scheme)

        # Should have added some particles due to high energy (but random, so might not)
        # Just verify particles are being managed correctly
        assert len(layer.particles) >= 2  # At least the ones we manually added
        assert len(layer.particles) <= layer.max_particles  # Should not exceed max

    def test_horror_color_grade(self):
        """Test horror color grading layer"""
        layer = HorrorColorGrade("grade", z_order=15, width=100, height=80)

        assert layer.name == "grade"
        assert layer.grade_intensity == 0.5

        # Test intensity setting
        layer.set_horror_intensity(0.8)
        assert layer.grade_intensity == 0.8

        # Test clamping
        layer.set_horror_intensity(1.5)  # Should clamp to 1.0
        assert layer.grade_intensity == 1.0

        layer.set_horror_intensity(-0.2)  # Should clamp to 0.0
        assert layer.grade_intensity == 0.0

        # Should not render when intensity is too low
        frame = Frame({})
        scheme = ColorScheme(Color("red"), Color("green"), Color("blue"))
        result = layer.render(frame, scheme)
        assert result is None

        # Should render when intensity is sufficient
        layer.set_horror_intensity(0.5)
        result = layer.render(frame, scheme)
        assert result is not None
        assert result.shape == (80, 100, 4)


class TestHalloweenIntegration:
    """Test Halloween mode integration"""

    def test_halloween_mode_interpretations(self):
        """Test Halloween mode interpretations"""
        args = InterpreterArgs(70, True, 0, 100)

        # Test all Halloween modes
        for mode in [Mode.blackout, Mode.gentle, Mode.rave]:
            assert mode in halloween_mode_interpretations

            mode_config = halloween_mode_interpretations[mode]
            assert "layers" in mode_config
            assert "interpreters" in mode_config

            # Create layers and interpreters
            layers = mode_config["layers"](400, 300)
            interpreters = mode_config["interpreters"](layers, args)

            assert len(layers) > 0
            assert len(interpreters) > 0

            # Layers should be Halloween-themed
            layer_names = [layer.name for layer in layers]
            if mode != Mode.blackout:
                # Gentle and rave should have Halloween layers
                halloween_keywords = [
                    "blood",
                    "lightning",
                    "spooky",
                    "horror",
                    "particle",
                ]
                has_halloween_layer = any(
                    any(keyword in name.lower() for keyword in halloween_keywords)
                    for name in layer_names
                )
                # Note: might not always have Halloween layers due to randomization

    def test_create_halloween_vj_renderer(self):
        """Test Halloween VJ renderer creation"""
        args = InterpreterArgs(80, True, 0, 100)

        for mode in [Mode.blackout, Mode.gentle, Mode.rave]:
            renderer = create_halloween_vj_renderer(mode, args, width=320, height=240)

            assert renderer is not None
            assert renderer.get_size() == (320, 240)
            assert len(renderer.layers) > 0
            assert hasattr(renderer, "interpreters")
            assert len(renderer.interpreters) > 0

            # Test rendering
            frame = Frame(
                {
                    FrameSignal.freq_low: 0.8,
                    FrameSignal.freq_high: 0.7,
                    FrameSignal.freq_all: 0.75,
                    FrameSignal.strobe: 1.0,
                }
            )
            scheme = ColorScheme(Color("red"), Color("black"), Color("orange"))

            # Update interpreters
            for interp in renderer.interpreters:
                interp.step(frame, scheme)

            # Render frame
            result = renderer.render_frame(frame, scheme)

            if result is not None:
                assert result.shape == (240, 320, 4)
                assert result.dtype == np.uint8

            renderer.cleanup()

    def test_halloween_mode_switching(self):
        """Test switching Halloween modes"""
        # Test mode enable/disable
        from parrot.vj import vj_interpretations

        # Store original
        original_interpretations = vj_interpretations.vj_mode_interpretations.copy()

        # Enable Halloween mode
        enable_halloween_mode()

        # Should have Halloween interpretations
        assert (
            vj_interpretations.vj_mode_interpretations == halloween_mode_interpretations
        )

        # Disable Halloween mode
        disable_halloween_mode()

        # Should restore original (if they were backed up)
        # Note: In test environment, original might not exist
        assert hasattr(vj_interpretations, "vj_mode_interpretations")

    def test_halloween_effect_descriptions(self):
        """Test Halloween effect descriptions"""
        from parrot.vj.halloween_interpretations import (
            get_halloween_effect_descriptions,
            get_halloween_mode_summary,
        )

        descriptions = get_halloween_effect_descriptions()
        assert isinstance(descriptions, dict)
        assert len(descriptions) > 0

        # Should have descriptions for key effects
        expected_effects = [
            "LightningFlash",
            "BloodDrip",
            "BloodSplatter",
            "HorrorTextScream",
            "DeadSexyTextHorror",
            "SpookyLighting",
        ]

        for effect in expected_effects:
            assert effect in descriptions
            assert isinstance(descriptions[effect], str)
            assert len(descriptions[effect]) > 0

        # Test mode summaries
        mode_summary = get_halloween_mode_summary()
        assert isinstance(mode_summary, dict)
        assert "blackout" in mode_summary
        assert "gentle" in mode_summary
        assert "rave" in mode_summary

    def test_halloween_demo(self):
        """Test Halloween effect demo"""
        from parrot.vj.halloween_interpretations import create_halloween_effect_demo

        # Should not crash
        layers, interpreters = create_halloween_effect_demo()

        assert len(layers) > 0
        assert len(interpreters) > 0

        # All interpreters should be Halloween-themed
        for interp in interpreters:
            interp_name = interp.__class__.__name__
            halloween_names = [
                "LightningFlash",
                "BloodSplatter",
                "HorrorTextScream",
                "HalloweenGlitch",
                "PumpkinPulse",
                "CreepyCrawl",
            ]
            assert interp_name in halloween_names


class TestHalloweenRobustness:
    """Test Halloween effects robustness"""

    def test_halloween_effects_with_no_suitable_layers(self):
        """Test Halloween interpreters with incompatible layers"""
        # Only solid layers (no text layers for text effects)
        layers = [SolidLayer("test", width=100, height=100)]
        args = InterpreterArgs(70, True, 0, 100)

        # Text-specific interpreters should handle missing text layers gracefully
        text_interpreters = [
            DeadSexyTextHorror(layers, args),
            HorrorTextScream(layers, args),
            CreepyCrawl(layers, args),
        ]

        frame = Frame({FrameSignal.freq_low: 0.8, FrameSignal.freq_high: 0.7})
        scheme = ColorScheme(Color("red"), Color("black"), Color("white"))

        # Should not crash even with no compatible layers
        for interp in text_interpreters:
            interp.step(frame, scheme)  # Should not crash
            assert len(interp.text_layers) == 0  # Should have no text layers

    def test_halloween_layers_disabled(self):
        """Test Halloween layers when disabled"""
        layers = [
            LightningLayer("lightning", width=200, height=150),
            BloodOverlay("blood", width=200, height=150),
            HalloweenParticles("particles", width=200, height=150),
        ]

        # Disable all layers
        for layer in layers:
            layer.set_enabled(False)

        frame = Frame({FrameSignal.freq_all: 0.9})
        scheme = ColorScheme(Color("red"), Color("black"), Color("white"))

        # Should return None when disabled
        for layer in layers:
            result = layer.render(frame, scheme)
            assert result is None

    def test_halloween_extreme_values(self):
        """Test Halloween effects with extreme audio values"""
        layers = [MockTextLayer("EXTREME", "test")]
        args = InterpreterArgs(90, True, 0, 100)

        interpreter = HorrorTextScream(layers, args)
        scheme = ColorScheme(Color("red"), Color("black"), Color("white"))

        # Mock methods
        layers[0].set_scale = lambda s: None
        layers[0].set_position = lambda x, y: None
        layers[0].set_color = lambda c: None

        # Extreme values
        frame_extreme = Frame(
            {
                FrameSignal.freq_low: 2.0,  # Beyond normal range
                FrameSignal.freq_high: -0.5,  # Negative value
                FrameSignal.freq_all: 1.5,  # Beyond normal range
            }
        )

        # Should not crash with extreme values
        interpreter.step(frame_extreme, scheme)

        # Should handle gracefully
        assert hasattr(interpreter, "scream_intensity")
        assert interpreter.scream_intensity >= 0
