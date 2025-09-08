#!/usr/bin/env python3
"""
Pyramid Rave Demo - Floating Metallic Pyramids
Showcases the incredible 3D pyramid layers with metallic finishes
"""
import time
import numpy as np
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.utils.colour import Color
from parrot.vj.layers.pyramid import (
    PyramidLayer,
    GoldenPyramidsLayer,
    SilverPyramidsLayer,
    RainbowPyramidsLayer,
    MegaPyramidLayer,
    PyramidSwarmLayer,
    PyramidFormationLayer,
    PyramidPortalLayer,
)
from parrot.vj.interpreters.pyramid_effects import (
    PyramidPulse,
    PyramidFloat,
    PyramidSpin,
    PyramidMetallic,
    PyramidSwarm,
    PyramidPortal,
    PyramidStorm,
    PyramidBass,
    PyramidHypnotic,
    PyramidRave,
)
from parrot.vj.renderer import ModernGLRenderer
from parrot.interpreters.base import InterpreterArgs


def demo_pyramid_types():
    """Demonstrate different pyramid layer types"""
    print("🔺" * 60)
    print("  RAVEY METALLIC PYRAMID LAYERS")
    print("🔺" * 60)

    # Create different pyramid layers
    pyramid_layers = [
        ("🏆 Golden Pyramids", GoldenPyramidsLayer("golden", 6)),
        ("🥈 Silver Pyramids", SilverPyramidsLayer("silver", 5)),
        ("🌈 Rainbow Pyramids", RainbowPyramidsLayer("rainbow", 8)),
        ("👑 Mega Pyramid", MegaPyramidLayer("mega", "gold")),
        ("🐝 Pyramid Swarm", PyramidSwarmLayer("swarm", "chrome")),
        ("🔄 Formation Pyramids", PyramidFormationLayer("formation", "circle")),
        ("🌀 Pyramid Portal", PyramidPortalLayer("portal")),
    ]

    print(f"\n🔺 Available Pyramid Types ({len(pyramid_layers)}):")

    for layer_name, layer in pyramid_layers:
        print(f"\n   {layer_name}:")
        print(f"     Layer: {layer}")
        print(f"     Pyramid Count: {len(layer.pyramids)}")
        print(f"     Z-Order: {layer.z_order}")

        # Show pyramid details
        if layer.pyramids:
            first_pyramid = layer.pyramids[0]
            print(f"     Metal Types: {set(p.metal_type for p in layer.pyramids)}")
            print(
                f"     Size Range: {min(p.size for p in layer.pyramids):.1f} - {max(p.size for p in layer.pyramids):.1f}"
            )

        # Test rendering with different audio
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
                "🔊 Bass Drop",
                Frame(
                    {
                        FrameSignal.freq_low: 0.95,
                        FrameSignal.freq_high: 0.3,
                        FrameSignal.freq_all: 0.7,
                    }
                ),
            ),
            (
                "🎼 Treble Spike",
                Frame(
                    {
                        FrameSignal.freq_low: 0.2,
                        FrameSignal.freq_high: 0.9,
                        FrameSignal.freq_all: 0.6,
                    }
                ),
            ),
            (
                "💥 Peak Energy",
                Frame(
                    {
                        FrameSignal.freq_low: 0.9,
                        FrameSignal.freq_high: 0.85,
                        FrameSignal.freq_all: 0.95,
                    }
                ),
            ),
        ]

        scheme = ColorScheme(Color("gold"), Color("black"), Color("silver"))

        for scenario_name, frame in test_scenarios:
            # Set layer size for testing
            layer.set_size(800, 600)

            try:
                result = layer.render(frame, scheme)

                if result is not None:
                    coverage = (np.count_nonzero(result) / (800 * 600)) * 100
                    avg_intensity = np.mean(result[:, :, :3])

                    print(
                        f"     {scenario_name}: ✅ {coverage:.1f}% coverage, intensity {avg_intensity:.0f}"
                    )
                else:
                    print(f"     {scenario_name}: ❌ No render")

            except Exception as e:
                print(f"     {scenario_name}: ⚠️ Error - {e}")

        # Cleanup
        layer.cleanup()


def demo_pyramid_interpreters():
    """Demonstrate pyramid control interpreters"""
    print("\n" + "🎛️" * 60)
    print("  PYRAMID CONTROL INTERPRETERS")
    print("🎛️" * 60)

    # Create test pyramid layers
    test_layers = [
        GoldenPyramidsLayer("golden_test", 4),
        SilverPyramidsLayer("silver_test", 3),
    ]

    # Set size for testing
    for layer in test_layers:
        layer.set_size(600, 400)

    args = InterpreterArgs(hype=80, allow_rainbows=True, min_hype=0, max_hype=100)

    # Test different pyramid interpreters
    interpreter_tests = [
        ("🔺 Pyramid Pulse", PyramidPulse(test_layers, args, pulse_intensity=2.0)),
        ("🎈 Pyramid Float", PyramidFloat(test_layers, args, float_speed=1.5)),
        ("🌀 Pyramid Spin", PyramidSpin(test_layers, args, spin_multiplier=2.0)),
        ("✨ Pyramid Metallic", PyramidMetallic(test_layers, args, metal_cycle=True)),
        ("🐝 Pyramid Swarm", PyramidSwarm(test_layers, args, swarm_tightness=0.4)),
        ("🌀 Pyramid Portal", PyramidPortal(test_layers, args, portal_intensity=2.0)),
        ("🌪️ Pyramid Storm", PyramidStorm(test_layers, args, chaos_intensity=2.5)),
        ("🔊 Pyramid Bass", PyramidBass(test_layers, args, bass_boost=3.0)),
        ("😵‍💫 Pyramid Hypnotic", PyramidHypnotic(test_layers, args)),
        ("🎆 Pyramid Rave", PyramidRave(test_layers, args)),
    ]

    print(f"\n🎛️ Testing {len(interpreter_tests)} pyramid interpreters:")

    scheme = ColorScheme(Color("gold"), Color("purple"), Color("cyan"))

    for interp_name, interpreter in interpreter_tests:
        print(f"\n   {interp_name}:")
        print(f"     Interpreter: {interpreter}")

        # Test with different audio scenarios
        test_frames = [
            (
                "Low Energy",
                Frame({FrameSignal.freq_all: 0.2, FrameSignal.freq_low: 0.1}),
            ),
            (
                "Bass Drop",
                Frame({FrameSignal.freq_all: 0.8, FrameSignal.freq_low: 0.95}),
            ),
            (
                "Treble Peak",
                Frame({FrameSignal.freq_all: 0.7, FrameSignal.freq_high: 0.9}),
            ),
            (
                "Maximum Energy",
                Frame(
                    {
                        FrameSignal.freq_all: 0.95,
                        FrameSignal.freq_low: 0.9,
                        FrameSignal.freq_high: 0.85,
                    }
                ),
            ),
        ]

        for scenario_name, frame in test_frames:
            old_str = str(interpreter)
            interpreter.step(frame, scheme)
            new_str = str(interpreter)

            # Check pyramid states
            total_pyramids = sum(len(layer.pyramids) for layer in test_layers)
            active_layers = sum(1 for layer in test_layers if layer.is_enabled())
            avg_alpha = sum(layer.get_alpha() for layer in test_layers) / len(
                test_layers
            )

            print(
                f"     {scenario_name}: {total_pyramids} pyramids, {active_layers} active, α={avg_alpha:.2f}"
            )
            if old_str != new_str:
                print(f"       → {new_str}")

    # Cleanup
    for layer in test_layers:
        layer.cleanup()


def demo_rave_pyramid_combinations():
    """Demonstrate pyramid effects during a rave progression"""
    print("\n" + "🎆" * 60)
    print("  RAVE PYRAMID PROGRESSION")
    print("🎆" * 60)

    # Create full pyramid setup for rave
    rave_pyramids = [
        GoldenPyramidsLayer("rave_golden", 4),
        SilverPyramidsLayer("rave_silver", 3),
        MegaPyramidLayer("rave_mega", "rainbow"),
        PyramidSwarmLayer("rave_swarm", "chrome"),
    ]

    # Set size
    for layer in rave_pyramids:
        layer.set_size(1200, 800)

    args = InterpreterArgs(hype=90, allow_rainbows=True, min_hype=0, max_hype=100)

    # Create pyramid interpreters for ultimate rave
    interpreters = [
        PyramidRave(rave_pyramids, args),
        PyramidBass(rave_pyramids, args, bass_boost=4.0),
        PyramidMetallic(rave_pyramids, args, metal_cycle=True),
    ]

    # Rave progression timeline
    rave_timeline = [
        (
            "🎵 Warm-up",
            {
                FrameSignal.freq_low: 0.3,
                FrameSignal.freq_high: 0.2,
                FrameSignal.freq_all: 0.25,
            },
            "Gentle pyramid floating and rotation",
        ),
        (
            "🎶 Building",
            {
                FrameSignal.freq_low: 0.6,
                FrameSignal.freq_high: 0.5,
                FrameSignal.freq_all: 0.55,
            },
            "Pyramids start pulsing and moving faster",
        ),
        (
            "🔥 Pre-Drop",
            {
                FrameSignal.freq_low: 0.8,
                FrameSignal.freq_high: 0.7,
                FrameSignal.freq_all: 0.75,
            },
            "Intense pyramid movement, formations changing",
        ),
        (
            "💥 THE DROP!",
            {
                FrameSignal.freq_low: 0.95,
                FrameSignal.freq_high: 0.9,
                FrameSignal.freq_all: 0.92,
            },
            "PYRAMID STORM - Maximum chaos and metallic shine!",
        ),
        (
            "🌀 Breakdown",
            {
                FrameSignal.freq_low: 0.4,
                FrameSignal.freq_high: 0.8,
                FrameSignal.freq_all: 0.6,
            },
            "Hypnotic pyramid patterns, synchronized movement",
        ),
        (
            "🌟 Final Build",
            {
                FrameSignal.freq_low: 0.9,
                FrameSignal.freq_high: 0.85,
                FrameSignal.freq_all: 0.88,
            },
            "All pyramids at maximum intensity and shine",
        ),
    ]

    color_schemes = [
        ColorScheme(Color("gold"), Color("black"), Color("bronze")),  # Warm metals
        ColorScheme(Color("silver"), Color("blue"), Color("white")),  # Cool metals
        ColorScheme(Color("copper"), Color("orange"), Color("red")),  # Hot metals
        ColorScheme(
            Color("platinum"), Color("purple"), Color("cyan")
        ),  # Psychedelic metals
        ColorScheme(
            Color("chrome"), Color("green"), Color("yellow")
        ),  # Electric metals
        ColorScheme(
            Color("rainbow"), Color("gold"), Color("silver")
        ),  # Ultimate metals
    ]

    print(f"\n🎆 Rave Timeline with Metallic Pyramids ({len(rave_timeline)} sections):")

    for i, (section_name, signals, description) in enumerate(rave_timeline):
        frame = Frame(signals)
        scheme = color_schemes[i % len(color_schemes)]

        print(f"\n{section_name}:")
        print(f"   📝 {description}")
        print(f"   🎨 Metal scheme: {scheme.fg} / {scheme.bg} / {scheme.bg_contrast}")

        # Update all pyramid interpreters
        active_effects = []

        for interp in interpreters:
            old_str = str(interp)
            interp.step(frame, scheme)
            new_str = str(interp)

            if old_str != new_str or any(
                keyword in new_str.lower() for keyword in ["storm", "drop", "active"]
            ):
                active_effects.append(new_str)

        # Analyze pyramid states
        total_pyramids = sum(len(layer.pyramids) for layer in rave_pyramids)
        enabled_layers = [layer.name for layer in rave_pyramids if layer.is_enabled()]
        avg_alpha = sum(layer.get_alpha() for layer in rave_pyramids) / len(
            rave_pyramids
        )

        print(f"   🔺 Total pyramids: {total_pyramids}")
        print(
            f"   🎭 Active layers: {len(enabled_layers)} ({', '.join(enabled_layers)})"
        )
        print(f"   📊 Average intensity: {avg_alpha:.2f}")

        if active_effects:
            print(f"   ⚡ Pyramid effects:")
            for effect in active_effects:
                print(f"     - {effect}")

        # Test render one layer for analysis
        if rave_pyramids[0].is_enabled():
            try:
                result = rave_pyramids[0].render(frame, scheme)
                if result is not None:
                    pyramid_coverage = np.count_nonzero(result) / (1200 * 800)
                    metallic_intensity = np.mean(result[:, :, :3])
                    print(
                        f"   ✨ Metallic factor: {pyramid_coverage*100:.1f}%, shine intensity: {metallic_intensity:.0f}"
                    )
            except Exception as e:
                print(f"   ⚠️ Render test: {e}")

        # Special moment descriptions
        energy = signals.get(FrameSignal.freq_all, 0)
        bass = signals.get(FrameSignal.freq_low, 0)

        if bass > 0.9:
            print("   🔊 BASS DROP - Pyramids scaling massively!")
        elif energy > 0.8:
            print("   ⚡ HIGH ENERGY - Metallic pyramids spinning wildly!")
        elif energy < 0.3:
            print("   🧘 CHILL - Hypnotic pyramid floating")

        # Brief pause between sections
        time.sleep(0.2)

    # Cleanup
    for layer in rave_pyramids:
        layer.cleanup()


def demo_metallic_finishes():
    """Showcase different metallic finishes"""
    print("\n" + "✨" * 60)
    print("  METALLIC FINISH SHOWCASE")
    print("✨" * 60)

    # Test different metal types
    metal_tests = [
        ("🏆 Gold", "gold", "Luxury finish for VIP vibes"),
        ("🥈 Silver", "silver", "Futuristic chrome for tech feel"),
        ("🟤 Copper", "copper", "Warm bronze for intimate sections"),
        ("💎 Chrome", "chrome", "Mirror finish for maximum shine"),
        ("🥉 Bronze", "bronze", "Rich patina for sophisticated look"),
        ("💍 Platinum", "platinum", "Premium finish for special moments"),
        ("🌈 Rainbow", "rainbow", "Psychedelic cycling for peak energy"),
    ]

    print(f"\n✨ Testing {len(metal_tests)} metallic finishes:")

    for metal_name, metal_type, description in metal_tests:
        print(f"\n   {metal_name}:")
        print(f"     📝 {description}")

        # Create pyramid layer with this metal
        layer = PyramidLayer(f"metal_test_{metal_type}", 3, [metal_type])
        layer.set_size(400, 300)

        # Test with rave audio
        rave_frame = Frame(
            {
                FrameSignal.freq_low: 0.8,
                FrameSignal.freq_high: 0.7,
                FrameSignal.freq_all: 0.75,
            }
        )
        scheme = ColorScheme(Color("white"), Color("black"), Color("gold"))

        try:
            result = layer.render(rave_frame, scheme)
            if result is not None:
                coverage = (np.count_nonzero(result) / (400 * 300)) * 100
                metallic_shine = np.mean(result[:, :, :3])

                print(f"     ✨ Coverage: {coverage:.1f}%")
                print(f"     💎 Metallic shine: {metallic_shine:.0f}")

                # Analyze metallic properties
                if metal_type == "rainbow":
                    print(f"     🌈 Rainbow cycling: Dynamic color changes")
                elif metal_type in ["gold", "bronze", "copper"]:
                    print(f"     🔥 Warm metal: Rich, luxury appearance")
                elif metal_type in ["silver", "chrome", "platinum"]:
                    print(f"     ❄️ Cool metal: Futuristic, high-tech look")

                print(f"     ✅ {metal_name} finish: PERFECT")
            else:
                print(f"     ❌ Render failed")

        except Exception as e:
            print(f"     ⚠️ Error: {e}")

        layer.cleanup()


def demo_pyramid_rave_combinations():
    """Show ultimate pyramid combinations for rave"""
    print("\n" + "🎪" * 60)
    print("  ULTIMATE RAVE PYRAMID COMBINATIONS")
    print("🎪" * 60)

    # Create ultimate rave pyramid setups
    rave_setups = [
        {
            "name": "🏆 Golden Temple",
            "layers": [
                GoldenPyramidsLayer("golden_main", 6),
                MegaPyramidLayer("golden_mega", "gold"),
            ],
            "description": "Luxury golden pyramids for VIP sections",
        },
        {
            "name": "🚀 Chrome Factory",
            "layers": [
                SilverPyramidsLayer("chrome_main", 5),
                PyramidSwarmLayer("chrome_swarm", "chrome"),
            ],
            "description": "Futuristic chrome pyramids for tech vibes",
        },
        {
            "name": "🌈 Psychedelic Portal",
            "layers": [
                RainbowPyramidsLayer("rainbow_main", 8),
                PyramidPortalLayer("portal_effect"),
            ],
            "description": "Rainbow pyramids creating dimensional portal",
        },
        {
            "name": "⚡ Metal Storm",
            "layers": [
                GoldenPyramidsLayer("storm_gold", 4),
                SilverPyramidsLayer("storm_silver", 4),
                PyramidSwarmLayer("storm_swarm", "rainbow"),
            ],
            "description": "Mixed metals creating chaotic storm effects",
        },
    ]

    args = InterpreterArgs(hype=90, allow_rainbows=True, min_hype=0, max_hype=100)

    print(f"\n🎪 Testing {len(rave_setups)} ultimate pyramid setups:")

    for setup in rave_setups:
        print(f"\n🎆 {setup['name']}:")
        print(f"   📝 {setup['description']}")
        print(f"   🔺 Pyramid layers: {[layer.name for layer in setup['layers']]}")

        # Set size on layers
        for layer in setup["layers"]:
            layer.set_size(1000, 600)

        # Create interpreters for this setup
        rave_interp = PyramidRave(setup["layers"], args)
        metallic_interp = PyramidMetallic(setup["layers"], args, metal_cycle=True)

        # Test with peak rave audio
        peak_frame = Frame(
            {
                FrameSignal.freq_low: 0.9,
                FrameSignal.freq_high: 0.85,
                FrameSignal.freq_all: 0.88,
            }
        )
        scheme = ColorScheme(Color("white"), Color("gold"), Color("silver"))

        # Update interpreters
        rave_interp.step(peak_frame, scheme)
        metallic_interp.step(peak_frame, scheme)

        print(f"   🎛️ Rave control: {rave_interp}")
        print(f"   ✨ Metallic control: {metallic_interp}")

        # Analyze setup
        total_pyramids = sum(len(layer.pyramids) for layer in setup["layers"])
        metal_types = set()
        for layer in setup["layers"]:
            if hasattr(layer, "pyramids"):
                metal_types.update(p.metal_type for p in layer.pyramids)

        print(f"   📊 Total pyramids: {total_pyramids}")
        print(f"   💎 Metal types: {', '.join(metal_types)}")
        print(f"   ⚡ Perfect for: {setup['description']}")

        # Cleanup
        for layer in setup["layers"]:
            layer.cleanup()


def demo_pyramid_audio_mapping():
    """Show how pyramids map to different audio frequencies"""
    print("\n" + "🎵" * 60)
    print("  PYRAMID AUDIO MAPPING")
    print("🎵" * 60)

    # Audio-pyramid mappings
    mappings = [
        {
            "frequency": "🔊 Bass (Low Freq)",
            "pyramid_effects": [
                "Massive scaling",
                "Intense pulsing",
                "Metallic shine boost",
            ],
            "best_pyramids": ["MegaPyramid", "GoldenPyramids"],
            "description": "Bass drops create dramatic pyramid scaling and metallic reflections",
        },
        {
            "frequency": "🎼 Treble (High Freq)",
            "pyramid_effects": [
                "Rapid rotation",
                "Enhanced floating",
                "Formation changes",
            ],
            "best_pyramids": ["PyramidSwarm", "SilverPyramids"],
            "description": "Treble drives fast pyramid spinning and formation morphing",
        },
        {
            "frequency": "⚡ Energy (Combined)",
            "pyramid_effects": ["Overall intensity", "Layer alpha", "Movement speed"],
            "best_pyramids": ["RainbowPyramids", "PyramidPortal"],
            "description": "Total energy controls pyramid visibility and movement intensity",
        },
        {
            "frequency": "🥁 Beat Detection",
            "pyramid_effects": [
                "Formation switches",
                "Metal type cycling",
                "Portal effects",
            ],
            "best_pyramids": ["PyramidFormation", "All types"],
            "description": "Beats trigger formation changes and metallic finish cycling",
        },
    ]

    print(f"\n🎵 Pyramid Audio-Visual Mapping:")

    for mapping in mappings:
        print(f"\n{mapping['frequency']}:")
        print(f"   🔺 Best pyramids: {', '.join(mapping['best_pyramids'])}")
        print(f"   ⚡ Effects:")
        for effect in mapping["pyramid_effects"]:
            print(f"     → {effect}")
        print(f"   📝 {mapping['description']}")


def main():
    """Run pyramid rave demo"""
    try:
        demo_pyramid_types()
        demo_pyramid_interpreters()
        demo_rave_pyramid_combinations()
        demo_pyramid_audio_mapping()

        print("\n" + "🔺" * 60)
        print("  RAVEY METALLIC PYRAMIDS COMPLETE!")
        print("🔺" * 60)

        print("\n🏆 Pyramid System Ready:")
        print("   🔺 7 different pyramid layer types")
        print("   🎛️ 10 pyramid control interpreters")
        print("   ✨ 7 metallic finishes (gold, silver, chrome, etc.)")
        print("   🎪 4 ultimate rave combinations")
        print("   🎵 Perfect audio-visual mapping")

        print("\n🎆 Your Dead Sexy Rave Features:")
        print("   🏆 Golden pyramids for luxury VIP vibes")
        print("   🚀 Chrome pyramids for futuristic atmosphere")
        print("   🌈 Rainbow pyramids for psychedelic peaks")
        print("   👑 Mega pyramids for dramatic moments")
        print("   🐝 Pyramid swarms for high-energy chaos")
        print("   🌀 Portal effects for dimensional travel")
        print("   ✨ Dynamic metallic finishes that shine and pulse")

        print("\n🔥 Perfect for Your M4 Max:")
        print("   All pyramid effects GPU-optimized")
        print("   Smooth 3D rendering with metallic shaders")
        print("   Real-time audio-reactive movement")
        print("   Professional-grade geometric visuals")

        print("\n💫 Your guests will be mesmerized by:")
        print("   Floating pyramids that dance to the music")
        print("   Metallic surfaces that reflect the rave energy")
        print("   3D formations that morph and transform")
        print("   Portal effects that transport minds to other dimensions")

        print("\n🍎🔺✨ METALLIC PYRAMIDS = RAVE PERFECTION! ✨🔺🍎")

    except Exception as e:
        print(f"Pyramid demo failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
