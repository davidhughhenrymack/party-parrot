#!/usr/bin/env python3
"""
VJ DSL Demo
Showcases the Domain Specific Language for VJ interpreter configuration
"""
import numpy as np
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode
from parrot.interpreters.base import InterpreterArgs
from parrot.utils.colour import Color
from parrot.vj.dsl_interpretations import (
    vj_dsl_mode_interpretations,
    get_vj_dsl_setup,
    HalloweenBloodCombo,
    HalloweenLightningCombo,
    HalloweenTextCombo,
    create_epic_horror_combo,
)
from parrot.vj.dsl import (
    vj_randomize,
    vj_weighted_randomize,
    vj_combo,
    vj_with_args,
    for_video,
    for_text,
    for_laser,
    energy_gate,
    signal_switch,
)


def demo_dsl_syntax():
    """Demonstrate the VJ DSL syntax"""
    print("🎭" * 30)
    print("   VJ DSL SYNTAX DEMO")
    print("   'Express VJ effects like lighting fixtures'")
    print("🎭" * 30)

    print("\n🔤 DSL Syntax Examples:")

    # Show DSL examples
    dsl_examples = [
        {
            "name": "Basic Randomization",
            "code": "vj_randomize(BloodSplatter, BloodDrip, HorrorContrast)",
            "description": "Randomly selects one of the blood/horror effects",
        },
        {
            "name": "Weighted Selection",
            "code": "vj_weighted_randomize((70, BloodSplatter), (30, BloodDrip))",
            "description": "70% chance blood splatter, 30% chance blood drip",
        },
        {
            "name": "Effect Combination",
            "code": "vj_combo(BloodOnBass, LightningOnTreble, StrobeOnManual)",
            "description": "Combines multiple effects to work together",
        },
        {
            "name": "Layer Filtering",
            "code": "for_video(RedLightingOnBass)",
            "description": "Applies red lighting only to video layers",
        },
        {
            "name": "Custom Arguments",
            "code": 'vj_with_args("IntenseRed", RedLighting, red_intensity=3.0)',
            "description": "Creates red lighting with custom intensity",
        },
        {
            "name": "Energy Gating",
            "code": "energy_gate(0.8, LaserBurst)",
            "description": "Only activates laser burst above 80% energy",
        },
        {
            "name": "Signal Switching",
            "code": "signal_switch(StrobeFlash)",
            "description": "Changes strobe behavior based on audio signals",
        },
    ]

    for example in dsl_examples:
        print(f"\n📋 {example['name']}:")
        print(f"   Code: {example['code']}")
        print(f"   Effect: {example['description']}")


def demo_dsl_mode_configurations():
    """Demonstrate DSL mode configurations"""
    print("\n" + "🎪" * 30)
    print("   DSL MODE CONFIGURATIONS")
    print("🎪" * 30)

    args = InterpreterArgs(hype=80, allow_rainbows=True, min_hype=0, max_hype=100)

    for mode in [Mode.blackout, Mode.gentle, Mode.rave]:
        print(f"\n🎭 {mode.name.upper()} Mode DSL Configuration:")

        try:
            layers, interpreters = get_vj_dsl_setup(mode, args, width=800, height=600)

            print(f"   🎬 Layers ({len(layers)}):")
            for layer in layers:
                layer_emoji = (
                    "📺"
                    if "video" in layer.name.lower()
                    else (
                        "💀"
                        if "text" in layer.name.lower()
                        else (
                            "🔴"
                            if "laser" in layer.name.lower()
                            else (
                                "🩸"
                                if "blood" in layer.name.lower()
                                else "⚡" if "lightning" in layer.name.lower() else "🎨"
                            )
                        )
                    )
                )
                print(f"     {layer_emoji} {layer}")

            print(f"   ⚡ Interpreters ({len(interpreters)}):")
            for interp in interpreters:
                # Show DSL structure if available
                interp_name = str(interp)
                if hasattr(interp, "_vj_randomize_options"):
                    options = [opt.__name__ for opt in interp._vj_randomize_options]
                    interp_name += f" [randomize: {', '.join(options)}]"
                elif hasattr(interp, "_vj_combo_interpreters"):
                    combo_names = [
                        opt.__name__ for opt in interp._vj_combo_interpreters
                    ]
                    interp_name += f" [combo: {', '.join(combo_names)}]"

                print(f"     ✨ {interp_name}")

            # Test a frame to see effects in action
            frame = Frame(
                {
                    FrameSignal.freq_low: 0.7,
                    FrameSignal.freq_high: 0.6,
                    FrameSignal.freq_all: 0.65,
                    FrameSignal.strobe: 1.0 if mode == Mode.rave else 0.0,
                }
            )
            scheme = ColorScheme(Color("red"), Color("black"), Color("orange"))

            # Update interpreters
            active_effects = []
            for interp in interpreters:
                old_str = str(interp)
                interp.step(frame, scheme)
                new_str = str(interp)

                if old_str != new_str or any(
                    keyword in new_str.lower()
                    for keyword in ["active", "strobing", "bursting"]
                ):
                    active_effects.append(new_str)

            if active_effects:
                print(f"   🔥 Active effects: {len(active_effects)}")
                for effect in active_effects[:3]:  # Show first 3
                    print(f"     - {effect}")
                if len(active_effects) > 3:
                    print(f"     ... and {len(active_effects) - 3} more")

        except Exception as e:
            print(f"   ❌ Error: {e}")


def demo_dsl_combinations():
    """Demonstrate complex DSL combinations"""
    print("\n" + "🔧" * 30)
    print("   COMPLEX DSL COMBINATIONS")
    print("🔧" * 30)

    from parrot.vj.base import SolidLayer
    from parrot.vj.layers.video import MockVideoLayer
    from parrot.vj.layers.text import MockTextLayer
    from parrot.vj.layers.laser import LaserLayer

    # Create test layers
    layers = [
        SolidLayer("bg", width=600, height=400),
        MockVideoLayer("video"),
        MockTextLayer("DEMO", "text"),
        LaserLayer("lasers", width=600, height=400),
    ]

    args = InterpreterArgs(hype=85, allow_rainbows=True, min_hype=0, max_hype=100)

    # Test complex combinations
    combinations = [
        ("🩸 Blood Combo", HalloweenBloodCombo),
        ("⚡ Lightning Combo", HalloweenLightningCombo),
        ("💀 Text Combo", HalloweenTextCombo),
        ("🔴 Laser Combo", lambda l, a: None),  # Placeholder
        ("🎆 Epic Horror", create_epic_horror_combo()),
    ]

    scheme = ColorScheme(Color("red"), Color("black"), Color("white"))

    for combo_name, combo_factory in combinations:
        print(f"\n{combo_name}:")

        try:
            if callable(combo_factory):
                interpreter = combo_factory(layers, args)
            else:
                interpreter = combo_factory  # Already created

            print(f"   🎭 Created: {interpreter}")

            # Test with different energy levels
            test_frames = [
                (
                    "Low Energy",
                    Frame({FrameSignal.freq_all: 0.3, FrameSignal.freq_low: 0.4}),
                ),
                (
                    "High Energy",
                    Frame(
                        {
                            FrameSignal.freq_all: 0.9,
                            FrameSignal.freq_high: 0.8,
                            FrameSignal.strobe: 1.0,
                        }
                    ),
                ),
            ]

            for energy_name, frame in test_frames:
                old_str = str(interpreter)
                interpreter.step(frame, scheme)
                new_str = str(interpreter)

                if old_str != new_str:
                    print(f"     {energy_name}: {new_str}")
                else:
                    print(f"     {energy_name}: {old_str}")

        except Exception as e:
            print(f"   ❌ Error: {e}")


def demo_dsl_layer_filtering():
    """Demonstrate layer filtering in DSL"""
    print("\n" + "🔍" * 30)
    print("   DSL LAYER FILTERING")
    print("🔍" * 30)

    from parrot.vj.base import SolidLayer
    from parrot.vj.layers.video import MockVideoLayer
    from parrot.vj.layers.text import MockTextLayer
    from parrot.vj.layers.laser import LaserLayer
    from parrot.vj.interpreters.color_lighting import RedLighting
    from parrot.vj.interpreters.halloween_effects import DeadSexyTextHorror
    from parrot.vj.interpreters.laser_effects import ConcertLasers

    # Create mixed layer types
    layers = [
        SolidLayer("background", width=400, height=300),
        MockVideoLayer("horror_video"),
        MockTextLayer("FILTER", "demo_text"),
        LaserLayer("demo_lasers", width=400, height=300),
    ]

    args = InterpreterArgs(hype=75, allow_rainbows=True, min_hype=0, max_hype=100)

    # Test layer filtering
    filter_tests = [
        ("🎥 Video Only", for_video(RedLighting)),
        ("💀 Text Only", for_text(DeadSexyTextHorror)),
        ("🔴 Laser Only", for_laser(ConcertLasers)),
        ("🎨 All Layers", RedLighting),  # No filtering
    ]

    scheme = ColorScheme(Color("red"), Color("green"), Color("blue"))
    frame = Frame({FrameSignal.freq_low: 0.7, FrameSignal.freq_all: 0.6})

    print(f"\n🔍 Layer filtering tests:")
    print(f"   Available layers: {[l.name for l in layers]}")

    for filter_name, interpreter_factory in filter_tests:
        print(f"\n   {filter_name}:")

        try:
            interpreter = interpreter_factory(layers, args)

            # Check which layers the interpreter affects
            if hasattr(interpreter, "video_layers"):
                affected = [l.name for l in interpreter.video_layers]
                print(f"     Affects video layers: {affected}")
            elif hasattr(interpreter, "text_layers"):
                affected = [l.name for l in interpreter.text_layers]
                print(f"     Affects text layers: {affected}")
            elif hasattr(interpreter, "laser_layers"):
                affected = [l.name for l in interpreter.laser_layers]
                print(f"     Affects laser layers: {affected}")
            elif hasattr(interpreter, "layers"):
                affected = [l.name for l in interpreter.layers]
                print(f"     Affects all layers: {affected}")
            else:
                print(f"     Layer targeting: Unknown")

            print(f"     Interpreter: {interpreter}")

            # Test execution
            interpreter.step(frame, scheme)
            print(f"     ✅ Executed successfully")

        except Exception as e:
            print(f"     ❌ Error: {e}")


def demo_dsl_randomization():
    """Demonstrate DSL randomization features"""
    print("\n" + "🎲" * 30)
    print("   DSL RANDOMIZATION DEMO")
    print("🎲" * 30)

    from parrot.vj.base import SolidLayer
    from parrot.vj.interpreters.halloween_effects import (
        BloodSplatter,
        BloodDrip,
        HorrorContrast,
    )
    from parrot.vj.interpreters.laser_effects import (
        ConcertLasers,
        LaserMatrix,
        LaserBurst,
    )

    layers = [SolidLayer("test", width=300, height=200)]
    args = InterpreterArgs(hype=80, allow_rainbows=True, min_hype=0, max_hype=100)

    # Test randomization
    print(f"\n🎲 Testing randomization (10 iterations):")

    # Create randomized interpreter factory
    random_factory = vj_randomize(BloodSplatter, BloodDrip, HorrorContrast)

    selected_interpreters = []
    for i in range(10):
        interpreter = random_factory(layers, args)
        selected_interpreters.append(interpreter.__class__.__name__)

    print(f"   Options: BloodSplatter, BloodDrip, HorrorContrast")
    print(f"   Selected: {selected_interpreters}")

    # Count selections
    from collections import Counter

    counts = Counter(selected_interpreters)
    for interp_name, count in counts.items():
        percentage = (count / 10) * 100
        print(f"   {interp_name}: {count}/10 ({percentage:.0f}%)")

    # Test weighted randomization
    print(f"\n⚖️ Testing weighted randomization (10 iterations):")

    weighted_factory = vj_weighted_randomize(
        (70, ConcertLasers),  # 70% weight
        (20, LaserMatrix),  # 20% weight
        (10, LaserBurst),  # 10% weight
    )

    weighted_selections = []
    for i in range(10):
        interpreter = weighted_factory(layers, args)
        weighted_selections.append(interpreter.__class__.__name__)

    print(f"   Weights: ConcertLasers(70%), LaserMatrix(20%), LaserBurst(10%)")
    print(f"   Selected: {weighted_selections}")

    weighted_counts = Counter(weighted_selections)
    for interp_name, count in weighted_counts.items():
        percentage = (count / 10) * 100
        print(f"   {interp_name}: {count}/10 ({percentage:.0f}%)")


def demo_dsl_vs_traditional():
    """Compare DSL syntax vs traditional configuration"""
    print("\n" + "🔄" * 30)
    print("   DSL vs TRADITIONAL COMPARISON")
    print("🔄" * 30)

    print("\n📝 Traditional Configuration:")
    print(
        """
    # Traditional way (verbose, hard to read)
    if video_layers:
        video_effect = random.choice([
            AlphaFlash(video_layers, args, 
                      signal=FrameSignal.freq_high,
                      threshold=0.6, flash_alpha=1.0, base_alpha=0.3),
            AlphaPulse(video_layers, args,
                      signal=FrameSignal.freq_low, pulse_speed=0.25, 
                      min_alpha=0.2, max_alpha=1.0),
            HorrorContrast(video_layers, args,
                          contrast_range=(0.2, 3.0), response_speed=0.2)
        ])
        interpreters.append(video_effect)
    """
    )

    print("\n✨ DSL Configuration:")
    print(
        """
    # DSL way (clean, expressive, like lighting fixtures)
    for_video(
        vj_randomize(
            vj_with_args("IntenseFlash", AlphaFlash,
                        signal=FrameSignal.freq_high, threshold=0.6, 
                        flash_alpha=1.0, base_alpha=0.3),
            vj_with_args("HeavyPulse", AlphaPulse,
                        signal=FrameSignal.freq_low, pulse_speed=0.25, 
                        min_alpha=0.2, max_alpha=1.0),
            vj_with_args("HorrorContrast", HorrorContrast,
                        contrast_range=(0.2, 3.0), response_speed=0.2)
        )
    )
    """
    )

    print("\n🎯 DSL Benefits:")
    print("   ✅ More readable - clearly shows structure")
    print("   ✅ More maintainable - easy to modify")
    print("   ✅ More expressive - shows intent clearly")
    print("   ✅ Consistent with lighting system - same patterns")
    print("   ✅ Composable - easy to combine effects")
    print("   ✅ Debuggable - can inspect randomization options")


def demo_halloween_dsl_configuration():
    """Show the complete Halloween DSL configuration"""
    print("\n" + "🎃" * 30)
    print("   HALLOWEEN DSL CONFIGURATION")
    print("🎃" * 30)

    print("\n💀 Complete Halloween Rave Mode DSL:")
    print(
        """
Mode.rave: {
    "layers": lambda w, h: [
        SolidLayer("abyss", color=(10, 0, 0), z_order=0),
        HorrorVideo(w, h),
        BloodLayer(w, h),
        SpookyLightingLayer("demon_lights", num_lights=8),
        LightningLayer("lightning"),
        ParticleLayer(w, h, max_particles=25),
        HorrorColorGrade("blood_tint"),
        LaserHaze("demon_haze", haze_density=0.4),
        LaserLayer(w, h),
        DeadSexyText(w, h),
    ],
    "interpreters": [
        # Video effects with randomized lighting
        for_video(
            vj_combo(
                vj_randomize(
                    vj_with_args("IntenseFlash", AlphaFlash, threshold=0.6),
                    vj_with_args("HeavyPulse", AlphaPulse, pulse_speed=0.25),
                    vj_with_args("HorrorContrast", HorrorContrast, contrast_range=(0.2, 3.0))
                ),
                vj_with_args("AggressiveSwitch", VideoSelectorHype, energy_threshold=0.7),
                vj_randomize(
                    vj_with_args("BloodLighting", RedLighting, red_intensity=3.0),
                    vj_with_args("DynamicColor", DynamicColorLighting, beat_boost=True),
                    vj_with_args("ChannelSep", ColorChannelSeparation, separation_intensity=2.5)
                )
            )
        ),
        
        # Text effects - dramatic horror
        for_text(
            vj_randomize(
                vj_with_args("ScreamingText", HorrorTextScream, max_scale=3.0),
                vj_with_args("HorrorMode", DeadSexyTextHorror, shake_intensity=0.08),
                vj_with_args("GlitchText", HalloweenGlitch, glitch_intensity=0.8),
                vj_with_args("CrawlingText", CreepyCrawl, crawl_speed=0.04)
            )
        ),
        
        # Laser show - intense patterns
        for_laser(
            vj_weighted_randomize(
                (40, vj_with_args("WideFan", ConcertLasers, num_lasers=12, fan_angle=150.0)),
                (30, vj_with_args("DenseMatrix", LaserMatrix, grid_size=(8, 6))),
                (20, vj_with_args("Explosive", LaserBurst, max_burst_lasers=20)),
                (10, vj_with_args("FastChase", LaserChase, chase_speed=0.2))
            )
        ),
        
        # Strobing - maximum chaos
        signal_switch(
            vj_randomize(
                vj_with_args("HighSpeed", HighSpeedStrobe, max_frequency=60.0),
                AudioReactiveStrobe,
                vj_with_args("BeatSync", BeatStrobe, strobe_duration=4),
                vj_with_args("ColorCycle", ColorStrobe, strobe_speed=0.8)
            )
        ),
        
        # Energy-gated effects
        energy_gate(0.8,
            vj_combo(
                BloodOnBass,
                LightningOnTreble,
                StrobeOnManual
            )
        ),
    ]
}
    """
    )

    print("\n🎯 DSL Features Demonstrated:")
    print("   🎲 vj_randomize() - Random effect selection")
    print("   ⚖️ vj_weighted_randomize() - Weighted random selection")
    print("   🔗 vj_combo() - Combine multiple effects")
    print("   🎛️ vj_with_args() - Custom effect parameters")
    print("   🎯 for_video/text/laser() - Layer type filtering")
    print("   ⚡ energy_gate() - Energy-based activation")
    print("   🎵 signal_switch() - Audio signal switching")
    print("   🩸 BloodOnBass, LightningOnTreble - Predefined combinations")


def main():
    """Run the complete VJ DSL demo"""
    try:
        demo_dsl_syntax()
        demo_dsl_mode_configurations()
        demo_dsl_combinations()
        demo_dsl_layer_filtering()
        demo_dsl_randomization()
        demo_dsl_vs_traditional()
        demo_halloween_dsl_configuration()

        print("\n" + "🎭" * 40)
        print("  VJ DSL SYSTEM COMPLETE!")
        print("🎭" * 40)

        print("\n✨ DSL Features:")
        print("   🎲 Randomization - Like lighting fixture randomize()")
        print("   ⚖️ Weighted selection - Probability-based effect choice")
        print("   🔗 Effect combination - Multiple effects working together")
        print("   🎯 Layer filtering - Target specific layer types")
        print("   ⚡ Energy gating - Effects only above thresholds")
        print("   🎵 Signal switching - Behavior changes with audio")
        print("   🎛️ Custom arguments - Easy parameter customization")
        print("   📋 Pre-configured combos - Ready-to-use effect combinations")

        print("\n🎃 Halloween Integration:")
        print("   The DSL makes it easy to configure complex Halloween effects")
        print("   Randomization ensures variety in your horror show")
        print("   Layer filtering targets specific visual elements")
        print("   Energy gating creates escalating horror intensity")
        print("   Pre-configured combos provide instant spooky atmosphere")

        print("\n🔤 Just like the lighting system DSL!")
        print("   Your VJ effects are now as easy to configure as lighting fixtures")

    except Exception as e:
        print(f"Demo failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
