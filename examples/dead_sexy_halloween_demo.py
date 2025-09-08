#!/usr/bin/env python3
"""
Dead Sexy Halloween Party VJ Demo
Showcases all the spooky Halloween effects for the party!
"""
import time
import random
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
    get_halloween_effect_descriptions,
    get_halloween_mode_summary,
    create_halloween_effect_demo,
)


def demo_halloween_effects():
    """Demonstrate all Halloween effects"""
    print("🎃" * 20)
    print("  DEAD SEXY HALLOWEEN PARTY")
    print("     VJ EFFECTS DEMO")
    print("🎃" * 20)

    # Enable Halloween mode
    enable_halloween_mode()

    print("\n💀 Available Halloween Effects:")
    descriptions = get_halloween_effect_descriptions()
    for effect, desc in descriptions.items():
        print(f"  {desc}")

    print("\n🎭 Halloween Mode Configurations:")
    mode_summary = get_halloween_mode_summary()
    for mode, desc in mode_summary.items():
        print(f"  {mode.upper()}: {desc}")


def demo_dead_sexy_modes():
    """Demo each Halloween mode with Dead Sexy theme"""
    print("\n" + "=" * 50)
    print("DEAD SEXY MODE DEMONSTRATIONS")
    print("=" * 50)

    args = InterpreterArgs(hype=80, allow_rainbows=True, min_hype=0, max_hype=100)

    # Halloween party audio scenarios
    party_scenarios = [
        {
            "name": "Quiet Intro",
            "frame": Frame(
                {
                    FrameSignal.freq_low: 0.2,
                    FrameSignal.freq_high: 0.1,
                    FrameSignal.freq_all: 0.15,
                    FrameSignal.sustained_low: 0.3,
                }
            ),
        },
        {
            "name": "Building Energy",
            "frame": Frame(
                {
                    FrameSignal.freq_low: 0.6,
                    FrameSignal.freq_high: 0.5,
                    FrameSignal.freq_all: 0.55,
                    FrameSignal.sustained_low: 0.7,
                }
            ),
        },
        {
            "name": "DEAD SEXY DROP!",
            "frame": Frame(
                {
                    FrameSignal.freq_low: 0.95,
                    FrameSignal.freq_high: 0.9,
                    FrameSignal.freq_all: 0.92,
                    FrameSignal.sustained_low: 0.8,
                    FrameSignal.strobe: 1.0,
                }
            ),
        },
        {
            "name": "Creepy Breakdown",
            "frame": Frame(
                {
                    FrameSignal.freq_low: 0.3,
                    FrameSignal.freq_high: 0.8,
                    FrameSignal.freq_all: 0.55,
                    FrameSignal.pulse: 1.0,
                }
            ),
        },
    ]

    # Test each mode
    for mode in [Mode.gentle, Mode.rave]:
        print(f"\n👻 Testing {mode.name.upper()} mode:")

        try:
            renderer = create_halloween_vj_renderer(mode, args, width=400, height=300)

            print(f"  🎬 Layers ({len(renderer.layers)}):")
            for layer in renderer.layers:
                print(f"    - {layer}")

            print(f"  🎭 Effects ({len(renderer.interpreters)}):")
            for interp in renderer.interpreters:
                print(f"    - {interp}")

            # Test each party scenario
            for scenario in party_scenarios:
                print(f"\n    🎵 {scenario['name']}:")

                # Update interpreters with scenario
                for interp in renderer.interpreters:
                    interp.step(
                        scenario["frame"],
                        ColorScheme(Color("red"), Color("black"), Color("orange")),
                    )

                # Render frame
                result = renderer.render_frame(
                    scenario["frame"],
                    ColorScheme(Color("red"), Color("black"), Color("orange")),
                )

                if result is not None:
                    non_zero = np.count_nonzero(result)
                    print(f"      📺 Rendered: {result.shape}, pixels: {non_zero}")

                    # Analyze the visual content
                    if non_zero > 0:
                        avg_color = np.mean(result[result.sum(axis=2) > 0], axis=0)
                        print(
                            f"      🎨 Avg color: R{avg_color[0]:.0f} G{avg_color[1]:.0f} B{avg_color[2]:.0f}"
                        )
                else:
                    print("      📺 No render (blackout or error)")

            renderer.cleanup()

        except Exception as e:
            print(f"  ❌ Error in {mode.name}: {e}")

    print("\n" + "=" * 50)


def demo_interactive_halloween_effects():
    """Interactive demo of Halloween effects"""
    print("\n🕷️ INTERACTIVE HALLOWEEN EFFECTS DEMO 🕷️")
    print("Simulating a Dead Sexy party progression...")

    # Create Halloween renderer for rave mode
    args = InterpreterArgs(hype=85, allow_rainbows=True, min_hype=0, max_hype=100)
    renderer = create_halloween_vj_renderer(Mode.rave, args, width=600, height=400)

    # Simulate party progression
    party_progression = [
        ("🎵 Party starts - low energy", 0.2, 0.1),
        ("🎶 Music builds up", 0.4, 0.3),
        ("🔥 First drop hits!", 0.9, 0.8),
        ("💃 Dancing intensifies", 0.7, 0.9),
        ("⚡ Lightning moment!", 0.95, 0.95),
        ("🩸 Blood drop section", 0.8, 0.6),
        ("👻 Ghostly interlude", 0.3, 0.4),
        ("😈 DEAD SEXY FINALE!", 1.0, 1.0),
    ]

    color_schemes = [
        ColorScheme(Color("red"), Color("black"), Color("orange")),  # Classic Halloween
        ColorScheme(Color("purple"), Color("green"), Color("orange")),  # Witch colors
        ColorScheme(Color("orange"), Color("black"), Color("red")),  # Pumpkin theme
        ColorScheme(Color("white"), Color("red"), Color("black")),  # Ghost and blood
    ]

    print(f"\n🎬 Rendering {len(party_progression)} party moments...")

    for i, (moment_name, bass_level, treble_level) in enumerate(party_progression):
        print(f"\n{i+1}. {moment_name}")

        # Create frame for this moment
        frame = Frame(
            {
                FrameSignal.freq_low: bass_level,
                FrameSignal.freq_high: treble_level,
                FrameSignal.freq_all: (bass_level + treble_level) / 2,
                FrameSignal.sustained_low: bass_level * 0.8,
                FrameSignal.strobe: 1.0 if treble_level > 0.8 else 0.0,
                FrameSignal.pulse: 1.0 if bass_level > 0.8 else 0.0,
            }
        )

        scheme = color_schemes[i % len(color_schemes)]

        # Update all Halloween interpreters
        active_effects = []
        for interp in renderer.interpreters:
            old_str = str(interp)
            interp.step(frame, scheme)
            new_str = str(interp)

            # Check if effect is active (changed state)
            if old_str != new_str or any(
                keyword in new_str.lower()
                for keyword in ["active", "screaming", "splat", "scare"]
            ):
                active_effects.append(new_str)

        # Render the moment
        result = renderer.render_frame(frame, scheme)

        if result is not None:
            # Analyze the spookiness level
            red_intensity = np.mean(result[:, :, 0])
            darkness_level = np.sum(result[:, :, :3].sum(axis=2) < 50) / (
                result.shape[0] * result.shape[1]
            )

            print(f"   🎨 Red intensity: {red_intensity:.1f}/255 (blood level)")
            print(f"   🌑 Darkness: {darkness_level*100:.1f}% (spook factor)")

            if active_effects:
                print(f"   ⚡ Active effects: {', '.join(active_effects)}")

            # Special moments
            if bass_level > 0.9 and treble_level > 0.9:
                print("   💥 MAXIMUM HORROR INTENSITY!")
            elif bass_level > 0.8:
                print("   🩸 Blood effects likely active")
            elif treble_level > 0.8:
                print("   ⚡ Lightning strikes!")
        else:
            print("   🖤 Pure darkness...")

    renderer.cleanup()
    print("\n🎃 Interactive demo complete!")


def demo_dead_sexy_text_effects():
    """Demo the special Dead Sexy text effects"""
    print("\n" + "💀" * 25)
    print("    DEAD SEXY TEXT EFFECTS")
    print("💀" * 25)

    from parrot.vj.layers.text import TextLayer

    # Create text layer
    text_layer = TextLayer(
        "DEAD SEXY", "demo_text", alpha_mask=True, z_order=10, width=800, height=600
    )

    args = InterpreterArgs(hype=80, allow_rainbows=True, min_hype=0, max_hype=100)

    # Test different text effects
    text_effects = [
        ("Creepy Crawl", "🕷️"),
        ("Horror Scream", "😱"),
        ("Dead Sexy Horror", "💀"),
        ("Eerie Breathing", "🫁"),
    ]

    from parrot.vj.interpreters.halloween_effects import (
        CreepyCrawl,
        HorrorTextScream,
        DeadSexyTextHorror,
        EerieBreathing,
    )

    effect_classes = [CreepyCrawl, HorrorTextScream, DeadSexyTextHorror, EerieBreathing]

    for (effect_name, emoji), effect_class in zip(text_effects, effect_classes):
        print(f"\n{emoji} Testing {effect_name}:")

        interpreter = effect_class([text_layer], args)

        # Test with different energy levels
        test_frames = [
            (
                "Whisper",
                Frame({FrameSignal.freq_low: 0.1, FrameSignal.freq_high: 0.05}),
            ),
            ("Talking", Frame({FrameSignal.freq_low: 0.4, FrameSignal.freq_high: 0.3})),
            (
                "Shouting",
                Frame({FrameSignal.freq_low: 0.8, FrameSignal.freq_high: 0.7}),
            ),
            (
                "SCREAMING!",
                Frame({FrameSignal.freq_low: 0.95, FrameSignal.freq_high: 0.9}),
            ),
        ]

        scheme = ColorScheme(Color("darkred"), Color("black"), Color("orange"))

        for intensity_name, frame in test_frames:
            interpreter.step(frame, scheme)
            print(f"    {intensity_name}: {interpreter}")


def main():
    """Run the complete Dead Sexy Halloween demo"""
    try:
        demo_halloween_effects()
        demo_dead_sexy_modes()
        demo_interactive_halloween_effects()
        demo_dead_sexy_text_effects()

        print("\n" + "🎃" * 30)
        print("  DEAD SEXY HALLOWEEN VJ SYSTEM READY!")
        print("🎃" * 30)
        print("\n🕷️ To use in Party Parrot:")
        print(
            "   1. Run: from parrot.vj.halloween_interpretations import enable_halloween_mode"
        )
        print("   2. Run: enable_halloween_mode()")
        print("   3. Start Party Parrot and press SPACEBAR for VJ display")
        print("   4. Switch between modes to see different horror intensities!")
        print("\n💀 HAVE A DEAD SEXY HALLOWEEN! 💀")

    except Exception as e:
        print(f"Demo failed: {e}")
        import traceback

        traceback.print_exc()
    finally:
        # Always restore normal mode
        disable_halloween_mode()


if __name__ == "__main__":
    main()
