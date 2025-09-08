#!/usr/bin/env python3
"""
Dead Sexy Halloween Party with Color Lighting Effects
Complete demo showing Halloween effects + color lighting working together
"""
import numpy as np
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode
from parrot.interpreters.base import InterpreterArgs
from parrot.utils.colour import Color
from parrot.vj.halloween_interpretations import (
    enable_halloween_mode,
    disable_halloween_mode,
    create_halloween_vj_renderer,
)
from parrot.vj.interpreters.color_lighting import (
    RedLighting,
    ColorSchemeLighting,
    DynamicColorLighting,
    StrobeLighting,
)


def demo_dead_sexy_with_lighting():
    """Demonstrate Dead Sexy party with color lighting effects"""
    print("💀" * 25)
    print("  DEAD SEXY + COLOR LIGHTING")
    print("💀" * 25)

    # Enable Halloween mode
    enable_halloween_mode()

    try:
        # Create Halloween renderer for rave mode
        args = InterpreterArgs(hype=85, allow_rainbows=True, min_hype=0, max_hype=100)
        renderer = create_halloween_vj_renderer(Mode.rave, args, width=800, height=600)

        print(f"\n🎬 Halloween Rave Setup:")
        print(f"   Layers: {len(renderer.layers)}")
        for layer in renderer.layers:
            print(f"     - {layer}")

        print(f"\n   Effects: {len(renderer.interpreters)}")
        for interp in renderer.interpreters:
            print(f"     - {interp}")

        # Add additional color lighting effects to video layers
        video_layers = [l for l in renderer.layers if "video" in l.name.lower()]

        if video_layers:
            print(f"\n🔦 Adding Color Lighting to {len(video_layers)} video layers:")

            # Add red blood lighting for Halloween
            blood_lighting = RedLighting(video_layers, args, red_intensity=2.5)
            renderer.interpreters.append(blood_lighting)
            print(f"     + {blood_lighting}")

            # Add dynamic color cycling
            color_cycling = DynamicColorLighting(
                video_layers, args, intensity_range=(1.8, 3.5), beat_boost=True
            )
            renderer.interpreters.append(color_cycling)
            print(f"     + {color_cycling}")

        # Test party scenarios with color lighting
        party_moments = [
            {
                "name": "🎵 Creepy Intro",
                "frame": Frame(
                    {
                        FrameSignal.freq_low: 0.3,
                        FrameSignal.freq_high: 0.2,
                        FrameSignal.freq_all: 0.25,
                        FrameSignal.sustained_low: 0.4,
                    }
                ),
                "scheme": ColorScheme(
                    Color("darkred"), Color("black"), Color("orange")
                ),
            },
            {
                "name": "🩸 Blood Drop Section",
                "frame": Frame(
                    {
                        FrameSignal.freq_low: 0.85,
                        FrameSignal.freq_high: 0.6,
                        FrameSignal.freq_all: 0.75,
                        FrameSignal.sustained_low: 0.8,
                    }
                ),
                "scheme": ColorScheme(Color("red"), Color("black"), Color("white")),
            },
            {
                "name": "⚡ Lightning Strikes",
                "frame": Frame(
                    {
                        FrameSignal.freq_low: 0.7,
                        FrameSignal.freq_high: 0.95,
                        FrameSignal.freq_all: 0.82,
                        FrameSignal.strobe: 1.0,
                    }
                ),
                "scheme": ColorScheme(Color("white"), Color("blue"), Color("purple")),
            },
            {
                "name": "😈 DEAD SEXY FINALE!",
                "frame": Frame(
                    {
                        FrameSignal.freq_low: 0.98,
                        FrameSignal.freq_high: 0.96,
                        FrameSignal.freq_all: 0.97,
                        FrameSignal.sustained_low: 0.9,
                        FrameSignal.strobe: 1.0,
                        FrameSignal.pulse: 1.0,
                    }
                ),
                "scheme": ColorScheme(Color("red"), Color("orange"), Color("black")),
            },
        ]

        print(f"\n🎭 Testing {len(party_moments)} party moments:")

        for moment in party_moments:
            print(f"\n{moment['name']}:")

            # Update all interpreters (Halloween + color lighting)
            active_effects = []
            for interp in renderer.interpreters:
                old_str = str(interp)
                interp.step(moment["frame"], moment["scheme"])
                new_str = str(interp)

                # Track active effects
                if old_str != new_str or any(
                    keyword in new_str.lower()
                    for keyword in [
                        "active",
                        "screaming",
                        "splat",
                        "scare",
                        "boost",
                        "lightning",
                    ]
                ):
                    active_effects.append(new_str)

            # Render the moment
            result = renderer.render_frame(moment["frame"], moment["scheme"])

            if result is not None:
                # Analyze the visual output
                red_intensity = np.mean(result[:, :, 0])
                green_intensity = np.mean(result[:, :, 1])
                blue_intensity = np.mean(result[:, :, 2])
                total_brightness = red_intensity + green_intensity + blue_intensity

                # Calculate color dominance
                if red_intensity > green_intensity and red_intensity > blue_intensity:
                    dominant_color = f"🔴 Red-dominant ({red_intensity:.0f})"
                elif (
                    blue_intensity > red_intensity and blue_intensity > green_intensity
                ):
                    dominant_color = f"🔵 Blue-dominant ({blue_intensity:.0f})"
                elif (
                    green_intensity > red_intensity and green_intensity > blue_intensity
                ):
                    dominant_color = f"🟢 Green-dominant ({green_intensity:.0f})"
                else:
                    dominant_color = f"⚪ Balanced ({total_brightness/3:.0f})"

                print(f"   📺 Rendered: {result.shape}")
                print(f"   🎨 Color: {dominant_color}")
                print(f"   💡 Brightness: {total_brightness:.0f}/765 total")

                if active_effects:
                    print(f"   ⚡ Active effects:")
                    for effect in active_effects[:5]:  # Show first 5 to avoid clutter
                        print(f"      - {effect}")
                    if len(active_effects) > 5:
                        print(f"      ... and {len(active_effects) - 5} more")

                # Special moment analysis
                if red_intensity > 100:
                    print("   🩸 Strong blood/red lighting detected!")
                if blue_intensity > 100:
                    print("   ⚡ Lightning/ghost lighting active!")
                if total_brightness > 400:
                    print("   💥 HIGH INTENSITY MOMENT!")
                elif total_brightness < 100:
                    print("   🌑 Dark and spooky...")
            else:
                print("   🖤 Pure darkness...")

        renderer.cleanup()

    finally:
        disable_halloween_mode()


def demo_color_lighting_comparison():
    """Compare video with and without color lighting"""
    print("\n" + "🔦" * 30)
    print("   COLOR LIGHTING COMPARISON")
    print("   'Before vs After Color Enhancement'")
    print("🔦" * 30)

    from parrot.vj.layers.video import MockVideoLayer

    # Create two identical video layers
    video_without = MockVideoLayer("no_lighting", width=400, height=300)
    video_with = MockVideoLayer("with_lighting", width=400, height=300)

    # Set same base color
    base_color = (120, 80, 100)  # Purplish-gray
    video_without.color = base_color
    video_with.color = base_color

    args = InterpreterArgs(hype=60, allow_rainbows=True, min_hype=0, max_hype=100)

    # Create red lighting interpreter for one layer
    red_lighting = RedLighting([video_with], args, red_intensity=2.0)

    # Test scenarios
    scenarios = [
        ("Low Bass", Frame({FrameSignal.freq_low: 0.2})),
        ("Medium Bass", Frame({FrameSignal.freq_low: 0.5})),
        ("High Bass", Frame({FrameSignal.freq_low: 0.9})),
    ]

    scheme = ColorScheme(Color("red"), Color("black"), Color("white"))

    print(f"\n🎬 Base video color: RGB{base_color}")

    for scenario_name, frame in scenarios:
        print(f"\n🎵 {scenario_name}:")

        # Reset colors
        video_without.color = base_color
        video_with.color = base_color

        # Track color changes for lit video
        colors_applied = []
        original_set_color = video_with.set_color
        video_with.set_color = lambda c: colors_applied.append(c)

        # Apply lighting
        red_lighting.step(frame, scheme)

        # Restore method
        video_with.set_color = original_set_color

        # Compare results
        without_color = video_without.color
        with_color = colors_applied[-1] if colors_applied else video_with.color

        print(f"   Without lighting: RGB{without_color}")
        print(f"   With red lighting: RGB{with_color}")

        # Calculate enhancement
        if without_color[0] > 0:
            red_enhancement = with_color[0] / without_color[0]
            print(f"   🔴 Red enhancement: {red_enhancement:.2f}x")


def main():
    """Run the complete Dead Sexy + Color Lighting demo"""
    try:
        demo_dead_sexy_with_lighting()
        demo_color_lighting_comparison()

        print("\n" + "🎨" * 40)
        print("  DEAD SEXY COLOR LIGHTING COMPLETE!")
        print("🎨" * 40)

        print("\n✨ What you've seen:")
        print("   💀 Halloween horror effects (lightning, blood, screaming text)")
        print("   🔴 Red lighting picking out red/white video content")
        print("   🌈 Dynamic color cycling through the color scheme")
        print("   ⚡ Strobe lighting with Halloween colors")
        print("   🎯 Selective color enhancement based on audio")
        print("   🔦 Color scheme integration with multiplicative lighting")

        print("\n🎃 For your Dead Sexy party:")
        print("   1. Enable Halloween mode")
        print("   2. Color lighting will automatically enhance video content")
        print("   3. Red lighting picks out blood/red elements in videos")
        print("   4. Blue lighting creates ghostly/ethereal effects")
        print("   5. Dynamic lighting cycles through your color scheme")
        print("   6. All effects respond to bass, treble, and energy in real-time!")

        print("\n💀 Your party videos will look DEAD SEXY! 🎃")

    except Exception as e:
        print(f"Demo failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
