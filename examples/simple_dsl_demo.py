#!/usr/bin/env python3
"""
Simple VJ DSL Demo
Shows the basic DSL syntax working like mode_interpretations.py
"""
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode
from parrot.interpreters.base import InterpreterArgs
from parrot.utils.colour import Color
from parrot.vj.base import SolidLayer
from parrot.vj.layers.video import MockVideoLayer
from parrot.vj.layers.text import MockTextLayer

# Import DSL functions
from parrot.vj.dsl import (
    vj_randomize,
    vj_weighted_randomize,
    vj_combo,
    vj_with_args,
    for_video,
    for_text,
)

# Import VJ interpreters
from parrot.vj.interpreters.alpha_fade import AlphaFade, AlphaFlash
from parrot.vj.interpreters.halloween_effects import (
    BloodSplatter,
    BloodDrip,
    HorrorContrast,
)
from parrot.vj.interpreters.color_lighting import RedLighting
from parrot.vj.interpreters.strobe_effects import StrobeFlash, BeatStrobe


def demo_basic_dsl():
    """Demonstrate basic DSL syntax"""
    print("🎭" * 25)
    print("  VJ DSL LIKE LIGHTING FIXTURES")
    print("🎭" * 25)

    # Create test layers
    layers = [
        SolidLayer("background", width=400, height=300),
        MockVideoLayer("video"),
        MockTextLayer("DEAD SEXY", "text"),
    ]

    args = InterpreterArgs(hype=75, allow_rainbows=True, min_hype=0, max_hype=100)
    scheme = ColorScheme(Color("red"), Color("black"), Color("orange"))

    print("\n🎯 DSL Examples (like lighting mode_interpretations.py):")

    # Example 1: Basic randomization (like lighting)
    print("\n1️⃣ Basic Randomization:")
    print("   DSL: vj_randomize(BloodSplatter, BloodDrip, HorrorContrast)")

    random_interpreter = vj_randomize(BloodSplatter, BloodDrip, HorrorContrast)(
        layers, args
    )
    print(f"   Selected: {random_interpreter}")

    # Example 2: Weighted randomization (like lighting)
    print("\n2️⃣ Weighted Selection:")
    print("   DSL: vj_weighted_randomize((80, BloodSplatter), (20, BloodDrip))")

    weighted_interpreter = vj_weighted_randomize((80, BloodSplatter), (20, BloodDrip))(
        layers, args
    )
    print(f"   Selected: {weighted_interpreter}")

    # Example 3: Combination (like lighting combo())
    print("\n3️⃣ Effect Combination:")
    print("   DSL: vj_combo(AlphaFade, RedLighting)")

    combo_interpreter = vj_combo(
        vj_with_args("GentleFade", AlphaFade, signal=FrameSignal.sustained_low),
        vj_with_args("BloodGlow", RedLighting, red_intensity=2.0),
    )(layers, args)
    print(f"   Created: {combo_interpreter}")

    # Example 4: Layer filtering
    print("\n4️⃣ Layer Filtering:")
    print("   DSL: for_video(RedLighting)")

    video_only = for_video(RedLighting)(layers, args)
    print(f"   Video-only interpreter: {video_only}")

    # Example 5: Custom arguments
    print("\n5️⃣ Custom Arguments:")
    print("   DSL: vj_with_args('IntenseStrobe', StrobeFlash, strobe_frequency=20.0)")

    custom_strobe = vj_with_args("IntenseStrobe", StrobeFlash, strobe_frequency=20.0)(
        layers, args
    )
    print(f"   Custom interpreter: {custom_strobe}")

    # Test all interpreters with audio
    print("\n🎵 Testing with audio:")
    frame = Frame(
        {
            FrameSignal.freq_low: 0.8,
            FrameSignal.freq_high: 0.7,
            FrameSignal.freq_all: 0.75,
            FrameSignal.strobe: 1.0,
        }
    )

    test_interpreters = [
        ("Random", random_interpreter),
        ("Weighted", weighted_interpreter),
        ("Combo", combo_interpreter),
        ("Video-only", video_only),
        ("Custom", custom_strobe),
    ]

    for name, interp in test_interpreters:
        try:
            old_str = str(interp)
            interp.step(frame, scheme)
            new_str = str(interp)

            print(f"   {name}: {new_str}")
        except Exception as e:
            print(f"   {name}: Error - {e}")


def demo_halloween_dsl_style():
    """Show Halloween mode configuration in DSL style"""
    print("\n" + "🎃" * 25)
    print("  HALLOWEEN DSL CONFIGURATION")
    print("🎃" * 25)

    print("\n💀 Halloween Rave Mode (DSL Style):")
    print(
        """
Mode.rave: {
    "layers": [
        Black(w, h),                    # Dark background
        HorrorVideo(w, h),             # Spooky videos
        BloodLayer(w, h),              # Blood effects layer
        LaserLayer(w, h),              # Concert lasers
        DeadSexyText(w, h),            # Horror font text
    ],
    "interpreters": [
        # Video gets random lighting effects
        for_video(
            vj_randomize(
                vj_with_args("BloodGlow", RedLighting, red_intensity=3.0),
                vj_with_args("GhostLight", BlueLighting, blue_intensity=2.0),
                vj_with_args("ColorCycle", DynamicColorLighting, beat_boost=True)
            )
        ),
        
        # Text gets random horror effects  
        for_text(
            vj_randomize(
                vj_with_args("Screaming", HorrorTextScream, max_scale=2.5),
                vj_with_args("Crawling", CreepyCrawl, crawl_speed=0.04),
                vj_with_args("Breathing", EerieBreathing, breath_speed=0.03)
            )
        ),
        
        # Lasers get weighted random shows
        for_laser(
            vj_weighted_randomize(
                (50, vj_with_args("Fan", ConcertLasers, num_lasers=12)),
                (30, vj_with_args("Matrix", LaserMatrix, grid_size=(8,6))),
                (20, vj_with_args("Burst", LaserBurst, max_burst_lasers=20))
            )
        ),
        
        # Blood effects triggered by bass
        for_blood(
            vj_combo(
                BloodOnBass,
                vj_with_args("Dripping", BloodDrip, drip_threshold=0.6)
            )
        ),
        
        # Strobing on manual control
        StrobeOnManual,
    ]
}
    """
    )

    print("\n✨ DSL Benefits:")
    print("   📖 Readable - Clear structure like lighting fixtures")
    print("   🎲 Randomizable - Easy effect variation")
    print("   🔧 Composable - Combine effects naturally")
    print("   🎯 Filterable - Target specific layer types")
    print("   🎛️ Configurable - Easy parameter customization")
    print("   🔄 Maintainable - Simple to modify and extend")


def demo_dsl_comparison():
    """Compare DSL vs traditional syntax"""
    print("\n" + "🔄" * 25)
    print("  DSL vs TRADITIONAL SYNTAX")
    print("🔄" * 25)

    print("\n❌ Traditional (verbose, hard to maintain):")
    print(
        """
    video_layers = [l for l in layers if 'video' in l.name.lower()]
    if video_layers:
        lighting_effect = random.choice([
            RedLighting(video_layers, args, red_intensity=2.0, 
                       response_signal=FrameSignal.freq_low),
            BlueLighting(video_layers, args, blue_intensity=1.8,
                        response_signal=FrameSignal.freq_high),
            DynamicColorLighting(video_layers, args, 
                               intensity_range=(1.5, 3.0), beat_boost=True)
        ])
        interpreters.append(lighting_effect)
    """
    )

    print("\n✅ DSL (clean, expressive, like lighting fixtures):")
    print(
        """
    for_video(
        vj_randomize(
            vj_with_args("BloodGlow", RedLighting, red_intensity=2.0),
            vj_with_args("GhostLight", BlueLighting, blue_intensity=1.8),
            vj_with_args("ColorCycle", DynamicColorLighting, beat_boost=True)
        )
    )
    """
    )

    print("\n🎯 DSL Advantages:")
    print("   🎲 Same randomize() syntax as lighting fixtures")
    print("   🔗 Same combo() syntax for combinations")
    print("   🎛️ Same with_args() syntax for parameters")
    print("   📖 More readable and maintainable")
    print("   🔄 Consistent with existing lighting DSL")
    print("   🎨 Easier to create complex configurations")


def main():
    """Run the VJ DSL demo"""
    try:
        demo_basic_dsl()
        demo_halloween_dsl_style()
        demo_dsl_comparison()

        print("\n" + "🎭" * 30)
        print("  VJ DSL SYSTEM COMPLETE!")
        print("🎭" * 30)

        print("\n🎯 What you've seen:")
        print("   🎲 vj_randomize() - Like lighting randomize()")
        print("   ⚖️ vj_weighted_randomize() - Probability-based selection")
        print("   🔗 vj_combo() - Like lighting combo()")
        print("   🎛️ vj_with_args() - Like lighting with_args()")
        print("   🎯 for_video/text/laser() - Layer type filtering")
        print("   ⚡ energy_gate() - Energy-based activation")
        print("   🎵 signal_switch() - Audio signal switching")

        print("\n🎃 Halloween Integration:")
        print("   The DSL makes Halloween effect configuration clean and readable")
        print("   You can easily randomize between different horror effects")
        print("   Layer filtering targets specific visual elements")
        print("   Pre-configured combos provide instant spooky atmosphere")

        print("\n🔤 Just like the lighting system!")
        print("   Your VJ effects now use the same DSL as lighting fixtures")
        print("   Easy to read, maintain, and extend")

    except Exception as e:
        print(f"Demo failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
