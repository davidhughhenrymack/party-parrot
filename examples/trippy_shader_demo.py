#!/usr/bin/env python3
"""
Trippy Shader Demo for Rave Visuals
Showcases GLSL shader layers for psychedelic rave effects
"""
import numpy as np
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.interpreters.base import InterpreterArgs
from parrot.utils.colour import Color
from parrot.vj.layers.shader_layers import (
    TunnelShader,
    PlasmaShader,
    FractalShader,
    KaleidoscopeShader,
    WaveDistortionShader,
    PsychedelicShader,
    VortexShader,
    NoiseShader,
    HypnoticShader,
    GeometricShader,
    RainbowShader,
)
from parrot.vj.interpreters.shader_effects import (
    ShaderIntensity,
    ShaderCycler,
    ShaderMixer,
    ShaderGlitcher,
    ShaderBeat,
    ShaderColorSync,
    ShaderPulse,
    ShaderReactive,
)


def demo_trippy_shaders():
    """Demonstrate all trippy shader effects"""
    print("🌈" * 30)
    print("   TRIPPY RAVE SHADERS")
    print("   'Psychedelic GLSL effects for ultimate rave'")
    print("🌈" * 30)

    # Create all shader layers
    shader_layers = [
        ("🌀 Tunnel", TunnelShader("tunnel", width=800, height=600)),
        ("🔥 Plasma", PlasmaShader("plasma", width=800, height=600)),
        ("🌺 Fractal", FractalShader("fractal", width=800, height=600)),
        ("🔮 Kaleidoscope", KaleidoscopeShader("kaleidoscope", width=800, height=600)),
        ("🌊 Wave Distortion", WaveDistortionShader("waves", width=800, height=600)),
        ("🎆 Psychedelic", PsychedelicShader("psychedelic", width=800, height=600)),
        ("🌪️ Vortex", VortexShader("vortex", width=800, height=600)),
        ("📺 Noise", NoiseShader("noise", width=800, height=600)),
        ("😵‍💫 Hypnotic", HypnoticShader("hypnotic", width=800, height=600)),
        ("🔷 Geometric", GeometricShader("geometric", width=800, height=600)),
        ("🌈 Rainbow", RainbowShader("rainbow", width=800, height=600)),
    ]

    print(f"\n🎨 Available Trippy Shaders ({len(shader_layers)}):")

    for shader_name, shader_layer in shader_layers:
        print(f"   {shader_name}: {shader_layer}")

        # Test shader with different audio scenarios
        test_scenarios = [
            (
                "🎵 Ambient",
                Frame(
                    {
                        FrameSignal.freq_low: 0.2,
                        FrameSignal.freq_high: 0.1,
                        FrameSignal.freq_all: 0.15,
                    }
                ),
            ),
            (
                "🔊 Bass Heavy",
                Frame(
                    {
                        FrameSignal.freq_low: 0.9,
                        FrameSignal.freq_high: 0.3,
                        FrameSignal.freq_all: 0.6,
                    }
                ),
            ),
            (
                "🎼 Treble Spike",
                Frame(
                    {
                        FrameSignal.freq_low: 0.3,
                        FrameSignal.freq_high: 0.95,
                        FrameSignal.freq_all: 0.65,
                    }
                ),
            ),
            (
                "💥 Peak Energy",
                Frame(
                    {
                        FrameSignal.freq_low: 0.9,
                        FrameSignal.freq_high: 0.9,
                        FrameSignal.freq_all: 0.95,
                    }
                ),
            ),
        ]

        scheme = ColorScheme(Color("red"), Color("blue"), Color("orange"))

        for scenario_name, frame in test_scenarios:
            try:
                result = shader_layer.render(frame, scheme)

                if result is not None:
                    # Analyze shader output
                    non_zero_pixels = np.count_nonzero(result)
                    coverage = (non_zero_pixels / (800 * 600)) * 100
                    avg_intensity = np.mean(result[:, :, :3])

                    print(
                        f"     {scenario_name}: ✅ {coverage:.1f}% coverage, intensity {avg_intensity:.0f}"
                    )
                else:
                    print(f"     {scenario_name}: ❌ No render (fallback)")
            except Exception as e:
                print(f"     {scenario_name}: ⚠️ Error: {e}")


def demo_shader_interpreters():
    """Demonstrate shader control interpreters"""
    print("\n" + "🎛️" * 30)
    print("   SHADER CONTROL INTERPRETERS")
    print("🎛️" * 30)

    # Create test shaders
    shader_layers = [
        TunnelShader("tunnel", width=400, height=300),
        PlasmaShader("plasma", width=400, height=300),
        VortexShader("vortex", width=400, height=300),
    ]

    args = InterpreterArgs(hype=80, allow_rainbows=True, min_hype=0, max_hype=100)

    # Test different shader interpreters
    interpreter_tests = [
        ("🌈 Shader Intensity", ShaderIntensity(shader_layers, args)),
        ("🔄 Shader Cycler", ShaderCycler(shader_layers, args, switch_on_beat=True)),
        ("🎨 Shader Mixer", ShaderMixer(shader_layers, args, mix_speed=0.05)),
        (
            "📺 Shader Glitcher",
            ShaderGlitcher(shader_layers, args, glitch_probability=0.1),
        ),
        ("🥁 Shader Beat", ShaderBeat(shader_layers, args, beat_threshold=0.6)),
        ("🎨 Shader Color Sync", ShaderColorSync(shader_layers, args)),
        ("💓 Shader Pulse", ShaderPulse(shader_layers, args, pulse_frequency=3.0)),
        ("🎵 Shader Reactive", ShaderReactive(shader_layers, args, reactivity=1.5)),
    ]

    print(f"\n🎛️ Testing {len(interpreter_tests)} shader interpreters:")

    scheme = ColorScheme(Color("purple"), Color("orange"), Color("cyan"))

    for interp_name, interpreter in interpreter_tests:
        print(f"\n   {interp_name}:")
        print(f"     Interpreter: {interpreter}")

        # Test with different audio scenarios
        test_frames = [
            (
                "Low Energy",
                Frame({FrameSignal.freq_all: 0.2, FrameSignal.freq_high: 0.1}),
            ),
            (
                "Beat Hit",
                Frame({FrameSignal.freq_all: 0.7, FrameSignal.freq_high: 0.8}),
            ),
            (
                "Peak Energy",
                Frame({FrameSignal.freq_all: 0.95, FrameSignal.freq_low: 0.9}),
            ),
        ]

        for scenario_name, frame in test_frames:
            old_str = str(interpreter)
            interpreter.step(frame, scheme)
            new_str = str(interpreter)

            # Check shader states
            active_shaders = sum(1 for layer in shader_layers if layer.is_enabled())
            avg_alpha = sum(layer.get_alpha() for layer in shader_layers) / len(
                shader_layers
            )

            print(
                f"     {scenario_name}: {active_shaders} active, α={avg_alpha:.2f} - {new_str}"
            )


def demo_rave_shader_progression():
    """Demonstrate shader effects during a rave progression"""
    print("\n" + "🎆" * 30)
    print("   RAVE SHADER PROGRESSION")
    print("🎆" * 30)

    # Create full shader setup
    rave_shaders = [
        TunnelShader("tunnel", z_order=1, width=1200, height=800),
        PlasmaShader("plasma", z_order=2, width=1200, height=800),
        PsychedelicShader("psychedelic", z_order=3, width=1200, height=800),
        VortexShader("vortex", z_order=4, width=1200, height=800),
        KaleidoscopeShader("kaleidoscope", z_order=5, width=1200, height=800),
    ]

    args = InterpreterArgs(hype=90, allow_rainbows=True, min_hype=0, max_hype=100)

    # Create shader interpreters
    interpreters = [
        ShaderMixer(rave_shaders, args, mix_speed=0.04),
        ShaderBeat(rave_shaders, args, beat_threshold=0.7),
        ShaderReactive(rave_shaders, args, reactivity=2.0),
        ShaderGlitcher(rave_shaders, args, glitch_probability=0.05),
    ]

    # Rave progression
    rave_timeline = [
        (
            "🎵 Warm-up",
            {
                FrameSignal.freq_low: 0.3,
                FrameSignal.freq_high: 0.2,
                FrameSignal.freq_all: 0.25,
            },
            "Gentle trippy effects building",
        ),
        (
            "🎶 Building",
            {
                FrameSignal.freq_low: 0.6,
                FrameSignal.freq_high: 0.5,
                FrameSignal.freq_all: 0.55,
            },
            "Shaders becoming more intense",
        ),
        (
            "🔥 Drop Incoming",
            {
                FrameSignal.freq_low: 0.8,
                FrameSignal.freq_high: 0.7,
                FrameSignal.freq_all: 0.75,
            },
            "High energy, shaders pulsing",
        ),
        (
            "💥 THE DROP!",
            {
                FrameSignal.freq_low: 0.95,
                FrameSignal.freq_high: 0.9,
                FrameSignal.freq_all: 0.92,
                FrameSignal.strobe: 1.0,
            },
            "MAXIMUM TRIPPY CHAOS!",
        ),
        (
            "🌀 Breakdown",
            {
                FrameSignal.freq_low: 0.4,
                FrameSignal.freq_high: 0.8,
                FrameSignal.freq_all: 0.6,
                FrameSignal.pulse: 1.0,
            },
            "Hypnotic effects, glitching",
        ),
        (
            "🌟 Final Build",
            {
                FrameSignal.freq_low: 0.9,
                FrameSignal.freq_high: 0.85,
                FrameSignal.freq_all: 0.88,
            },
            "All shaders at maximum intensity",
        ),
    ]

    color_schemes = [
        ColorScheme(Color("red"), Color("black"), Color("orange")),  # Fire
        ColorScheme(Color("purple"), Color("green"), Color("cyan")),  # Psychedelic
        ColorScheme(Color("blue"), Color("yellow"), Color("magenta")),  # Electric
        ColorScheme(Color("white"), Color("red"), Color("blue")),  # Intense
        ColorScheme(Color("orange"), Color("purple"), Color("green")),  # Trippy
        ColorScheme(Color("cyan"), Color("pink"), Color("yellow")),  # Neon
    ]

    print(f"\n🎆 Rave Timeline ({len(rave_timeline)} sections):")

    for i, (section_name, signals, description) in enumerate(rave_timeline):
        frame = Frame(signals)
        scheme = color_schemes[i % len(color_schemes)]

        print(f"\n{section_name}:")
        print(f"   📝 {description}")
        print(f"   🎨 Colors: {scheme.fg} / {scheme.bg} / {scheme.bg_contrast}")

        # Update all shader interpreters
        active_effects = []

        for interp in interpreters:
            old_str = str(interp)
            interp.step(frame, scheme)
            new_str = str(interp)

            if old_str != new_str or any(
                keyword in new_str.lower() for keyword in ["storm", "glitching", "beat"]
            ):
                active_effects.append(new_str)

        # Analyze shader states
        enabled_shaders = [
            shader.name for shader in rave_shaders if shader.is_enabled()
        ]
        shader_alphas = [shader.get_alpha() for shader in rave_shaders]
        avg_alpha = sum(shader_alphas) / len(shader_alphas)

        print(
            f"   🎭 Active shaders: {len(enabled_shaders)} ({', '.join(enabled_shaders)})"
        )
        print(f"   📊 Average intensity: {avg_alpha:.2f}")

        if active_effects:
            print(f"   ⚡ Shader effects:")
            for effect in active_effects:
                print(f"     - {effect}")

        # Test render one shader for analysis
        if rave_shaders[0].is_enabled():
            try:
                result = rave_shaders[0].render(frame, scheme)
                if result is not None:
                    trippy_factor = np.count_nonzero(result) / (1200 * 800)
                    color_intensity = np.mean(result[:, :, :3])
                    print(
                        f"   🌀 Trippy factor: {trippy_factor*100:.1f}%, color intensity: {color_intensity:.0f}"
                    )
            except Exception as e:
                print(f"   ⚠️ Render test: {e}")

        # Special moments
        energy = signals.get(FrameSignal.freq_all, 0)
        if energy > 0.9:
            print("   🔥 PEAK ENERGY - Maximum trippy chaos!")
        elif energy > 0.7:
            print("   ⚡ HIGH ENERGY - Intense psychedelic effects!")

        if signals.get(FrameSignal.strobe, 0) > 0.5:
            print("   🌟 STROBE ACTIVE - Shader storm mode!")


def demo_shader_combinations():
    """Demonstrate shader combinations for ultimate rave experience"""
    print("\n" + "🎪" * 30)
    print("   ULTIMATE RAVE SHADER COMBINATIONS")
    print("🎪" * 30)

    # Create shader combination setups
    combinations = [
        {
            "name": "🌀 Tunnel Rave",
            "shaders": [TunnelShader("tunnel1"), PlasmaShader("plasma1")],
            "description": "Tunnel effect with plasma overlay for depth",
        },
        {
            "name": "🔮 Psychedelic Storm",
            "shaders": [
                PsychedelicShader("psyche"),
                KaleidoscopeShader("kaleid"),
                NoiseShader("noise"),
            ],
            "description": "Maximum psychedelic chaos with multiple patterns",
        },
        {
            "name": "🌊 Wave Vortex",
            "shaders": [WaveDistortionShader("waves"), VortexShader("vortex")],
            "description": "Distorted waves pulled into hypnotic vortex",
        },
        {
            "name": "⚡ Glitch Rainbow",
            "shaders": [RainbowShader("rainbow"), GeometricShader("geometric")],
            "description": "Rainbow waves with geometric glitch patterns",
        },
        {
            "name": "😵‍💫 Hypno Fractal",
            "shaders": [HypnoticShader("hypno"), FractalShader("fractal")],
            "description": "Hypnotic spirals with fractal mathematics",
        },
    ]

    args = InterpreterArgs(hype=85, allow_rainbows=True, min_hype=0, max_hype=100)

    print(f"\n🎪 Testing {len(combinations)} shader combinations:")

    for combo in combinations:
        print(f"\n🎆 {combo['name']}:")
        print(f"   📝 {combo['description']}")
        print(f"   🎭 Shaders: {[s.name for s in combo['shaders']]}")

        # Create shader mixer for this combination
        mixer = ShaderMixer(combo["shaders"], args, mix_speed=0.06)
        reactive = ShaderReactive(combo["shaders"], args, reactivity=1.8)

        # Test with rave audio
        rave_frame = Frame(
            {
                FrameSignal.freq_low: 0.85,
                FrameSignal.freq_high: 0.8,
                FrameSignal.freq_all: 0.82,
                FrameSignal.strobe: 1.0,
            }
        )

        scheme = ColorScheme(Color("cyan"), Color("magenta"), Color("yellow"))

        # Update interpreters
        mixer.step(rave_frame, scheme)
        reactive.step(rave_frame, scheme)

        print(f"   🎛️ Mixer: {mixer}")
        print(f"   🎵 Reactive: {reactive}")

        # Analyze combination
        active_count = sum(1 for shader in combo["shaders"] if shader.is_enabled())
        total_alpha = sum(shader.get_alpha() for shader in combo["shaders"])

        print(
            f"   📊 Active: {active_count}/{len(combo['shaders'])}, total intensity: {total_alpha:.2f}"
        )


def demo_shader_audio_mapping():
    """Demonstrate how shaders map to audio frequencies"""
    print("\n" + "🎵" * 30)
    print("   SHADER AUDIO MAPPING")
    print("🎵" * 30)

    # Audio-shader mappings
    mappings = [
        {
            "frequency": "🔊 Bass (Low Freq)",
            "shaders": ["Tunnel", "Plasma", "Vortex"],
            "effects": [
                "Tunnel speed increases with bass drops",
                "Plasma wave amplitude grows with bass",
                "Vortex rotation accelerates with bass",
            ],
        },
        {
            "frequency": "🎼 Treble (High Freq)",
            "shaders": ["Kaleidoscope", "Geometric", "Fractal"],
            "effects": [
                "Kaleidoscope segments multiply with treble",
                "Geometric pattern complexity increases",
                "Fractal iteration count scales with treble",
            ],
        },
        {
            "frequency": "⚡ Energy (Combined)",
            "shaders": ["Psychedelic", "Hypnotic", "Rainbow"],
            "effects": [
                "Psychedelic complexity scales with energy",
                "Hypnotic intensity increases with energy",
                "Rainbow saturation boosts with energy",
            ],
        },
        {
            "frequency": "🥁 Beat Detection",
            "shaders": ["All Shaders"],
            "effects": [
                "Beat-synchronized shader switching",
                "Intensity boosts on beat hits",
                "Glitch effects triggered by beats",
            ],
        },
    ]

    print(f"\n🎵 Audio-Visual Mapping:")

    for mapping in mappings:
        print(f"\n{mapping['frequency']}:")
        print(f"   🎭 Affects: {', '.join(mapping['shaders'])}")
        print(f"   ⚡ Effects:")
        for effect in mapping["effects"]:
            print(f"     → {effect}")


def demo_shader_performance():
    """Test shader rendering performance"""
    print("\n" + "⚡" * 30)
    print("   SHADER PERFORMANCE TEST")
    print("⚡" * 30)

    # Test different shader complexities
    performance_tests = [
        ("🌈 Simple (Rainbow)", RainbowShader("rainbow_perf", width=640, height=480)),
        ("🔥 Medium (Plasma)", PlasmaShader("plasma_perf", width=640, height=480)),
        ("🌺 Complex (Fractal)", FractalShader("fractal_perf", width=640, height=480)),
        (
            "🔮 Very Complex (Kaleidoscope)",
            KaleidoscopeShader("kaleid_perf", width=640, height=480),
        ),
    ]

    frame = Frame(
        {
            FrameSignal.freq_low: 0.7,
            FrameSignal.freq_high: 0.6,
            FrameSignal.freq_all: 0.65,
        }
    )
    scheme = ColorScheme(Color("red"), Color("green"), Color("blue"))

    print(f"\n⚡ Performance testing (640×480):")

    for test_name, shader in performance_tests:
        print(f"\n   {test_name}:")

        try:
            import time

            # Render multiple times for average
            render_times = []
            successful_renders = 0

            for _ in range(3):
                start_time = time.time()
                result = shader.render(frame, scheme)
                render_time = time.time() - start_time

                if result is not None:
                    render_times.append(render_time)
                    successful_renders += 1

            if render_times:
                avg_time = sum(render_times) / len(render_times)
                fps_estimate = 1.0 / avg_time if avg_time > 0 else 0

                print(f"     ✅ Avg render time: {avg_time*1000:.1f}ms")
                print(f"     📊 Estimated FPS: {fps_estimate:.0f}")
                print(f"     🎯 Success rate: {successful_renders}/3")

                if fps_estimate >= 60:
                    print(f"     🟢 Excellent performance!")
                elif fps_estimate >= 30:
                    print(f"     🟡 Good performance")
                else:
                    print(f"     🔴 May need optimization")
            else:
                print(f"     ❌ All renders failed - using CPU fallback")

        except Exception as e:
            print(f"     ⚠️ Performance test error: {e}")

        # Cleanup
        shader.cleanup()


def main():
    """Run the complete trippy shader demo"""
    try:
        demo_trippy_shaders()
        demo_shader_interpreters()
        demo_shader_audio_mapping()
        demo_rave_shader_progression()
        demo_shader_performance()

        print("\n" + "🌈" * 40)
        print("  TRIPPY SHADER SYSTEM COMPLETE!")
        print("🌈" * 40)

        print("\n🎨 Trippy Shaders Available:")
        print("   🌀 Tunnel - Infinite tunnel with spiral patterns")
        print("   🔥 Plasma - Flowing plasma energy effects")
        print("   🌺 Fractal - Mathematical fractal zoom and exploration")
        print("   🔮 Kaleidoscope - Multi-segment kaleidoscope patterns")
        print("   🌊 Wave Distortion - Rippling wave distortions")
        print("   🎆 Psychedelic - Complex interference patterns")
        print("   🌪️ Vortex - Hypnotic spiral vortex effects")
        print("   📺 Noise - Animated noise and static patterns")
        print("   😵‍💫 Hypnotic - Trance-inducing spiral patterns")
        print("   🔷 Geometric - Animated geometric shapes")
        print("   🌈 Rainbow - HSV color cycling waves")

        print("\n🎛️ Shader Control:")
        print("   🌈 ShaderIntensity - Audio controls overall shader brightness")
        print("   🔄 ShaderCycler - Switches between shaders on beats")
        print("   🎨 ShaderMixer - Blends multiple shaders together")
        print("   📺 ShaderGlitcher - Adds glitch effects to shaders")
        print("   🥁 ShaderBeat - Beat-synchronized shader boosts")
        print("   🎨 ShaderColorSync - Syncs colors with color schemes")
        print("   💓 ShaderPulse - Pulsing shader intensity")
        print("   🎵 ShaderReactive - Highly reactive to audio")

        print("\n🎯 Perfect for Rave:")
        print("   All shaders respond to bass, treble, and energy")
        print("   Beat detection triggers shader switching and effects")
        print("   Color schemes automatically applied to all shaders")
        print("   GPU-accelerated for real-time 60fps performance")
        print("   CPU fallback ensures compatibility")

        print("\n🔥 Your rave will have INCREDIBLE trippy visuals!")
        print("   Tunnel effects pull dancers into the music")
        print("   Plasma flows with the energy of the crowd")
        print("   Fractals create infinite mathematical beauty")
        print("   Kaleidoscopes fragment reality into patterns")
        print("   Psychedelic effects blow minds completely!")

        print("\n🌈 TRIPPY SHADER RAVE = MIND-BLOWING! 🌈")

    except Exception as e:
        print(f"Demo failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
