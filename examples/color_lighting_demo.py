#!/usr/bin/env python3
"""
Color Lighting Effects Demo
Showcases multiplicative color lighting effects that pick out specific colors from video
"""
import numpy as np
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.interpreters.base import InterpreterArgs
from parrot.utils.colour import Color
from parrot.vj.layers.video import MockVideoLayer
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


def demo_color_lighting_effects():
    """Demonstrate all color lighting effects"""
    print("🎨" * 25)
    print("  COLOR LIGHTING EFFECTS DEMO")
    print("🎨" * 25)

    # Create test video layer
    video_layer = MockVideoLayer("demo_video", width=400, height=300)
    video_layer.color = (150, 100, 80)  # Warm brownish color as base

    args = InterpreterArgs(hype=60, allow_rainbows=True, min_hype=0, max_hype=100)

    # Test different lighting effects
    lighting_effects = [
        (
            "Color Scheme Lighting",
            ColorSchemeLighting([video_layer], args, color_source="fg"),
        ),
        ("Red Blood Lighting", RedLighting([video_layer], args, red_intensity=2.0)),
        ("Blue Ghost Lighting", BlueLighting([video_layer], args, blue_intensity=1.8)),
        ("Dynamic Cycling", DynamicColorLighting([video_layer], args, beat_boost=True)),
        (
            "Selective Red Enhancement",
            SelectiveLighting([video_layer], args, target_color=(1.0, 0.0, 0.0)),
        ),
        ("Halloween Strobe", StrobeLighting([video_layer], args)),
        ("Warm/Cool Temperature", WarmCoolLighting([video_layer], args)),
        ("Moving Spotlights", SpotlightEffect([video_layer], args, num_spots=3)),
        ("Channel Separation", ColorChannelSeparation([video_layer], args)),
    ]

    # Test scenarios
    scenarios = [
        (
            "🎵 Quiet ambient",
            Frame(
                {
                    FrameSignal.freq_low: 0.2,
                    FrameSignal.freq_high: 0.1,
                    FrameSignal.freq_all: 0.15,
                }
            ),
        ),
        (
            "🎶 Building bass",
            Frame(
                {
                    FrameSignal.freq_low: 0.8,
                    FrameSignal.freq_high: 0.3,
                    FrameSignal.freq_all: 0.55,
                }
            ),
        ),
        (
            "🔥 Treble spike",
            Frame(
                {
                    FrameSignal.freq_low: 0.3,
                    FrameSignal.freq_high: 0.9,
                    FrameSignal.freq_all: 0.6,
                }
            ),
        ),
        (
            "💥 Full energy",
            Frame(
                {
                    FrameSignal.freq_low: 0.95,
                    FrameSignal.freq_high: 0.9,
                    FrameSignal.freq_all: 0.92,
                    FrameSignal.strobe: 1.0,
                }
            ),
        ),
    ]

    # Color schemes to test
    schemes = [
        (
            "Classic Red/Black",
            ColorScheme(Color("red"), Color("black"), Color("white")),
        ),
        ("Blue/Orange", ColorScheme(Color("blue"), Color("orange"), Color("cyan"))),
        ("Purple/Green", ColorScheme(Color("purple"), Color("green"), Color("yellow"))),
        ("Halloween", ColorScheme(Color("orange"), Color("black"), Color("red"))),
    ]

    for effect_name, interpreter in lighting_effects:
        print(f"\n🔦 Testing {effect_name}:")
        print(f"   Effect: {interpreter}")

        for scheme_name, scheme in schemes:
            print(f"\n   🎨 Color Scheme: {scheme_name}")

            for scenario_name, frame in scenarios:
                # Reset video layer color for each test
                video_layer.color = (150, 100, 80)

                # Track color changes
                colors_applied = []

                def track_color(c):
                    colors_applied.append(c)
                    # Don't call original to avoid recursion

                original_set_color = video_layer.set_color
                video_layer.set_color = track_color

                # Apply lighting effect
                interpreter.step(frame, scheme)

                # Restore original method
                video_layer.set_color = original_set_color

                if colors_applied:
                    final_color = colors_applied[-1]
                    base_color = (150, 100, 80)

                    # Calculate color change
                    r_change = final_color[0] - base_color[0]
                    g_change = final_color[1] - base_color[1]
                    b_change = final_color[2] - base_color[2]

                    # Determine dominant change
                    changes = [("R", r_change), ("G", g_change), ("B", b_change)]
                    changes.sort(key=lambda x: abs(x[1]), reverse=True)
                    dominant_change = changes[0]

                    print(
                        f"     {scenario_name}: {final_color} "
                        f"(Δ{dominant_change[0]}{dominant_change[1]:+d})"
                    )
                else:
                    print(f"     {scenario_name}: No color change")

        print()


def demo_red_lighting_showcase():
    """Showcase red lighting picking out red/white parts"""
    print("\n" + "🔴" * 30)
    print("   RED LIGHTING SHOWCASE")
    print("   'Picks out red and white parts of video'")
    print("🔴" * 30)

    # Create video layers with different base colors
    test_videos = [
        ("Red Video", MockVideoLayer("red_video"), (200, 50, 50)),  # Mostly red
        ("White Video", MockVideoLayer("white_video"), (200, 200, 200)),  # White/gray
        ("Blue Video", MockVideoLayer("blue_video"), (50, 50, 200)),  # Mostly blue
        ("Green Video", MockVideoLayer("green_video"), (50, 200, 50)),  # Mostly green
        ("Mixed Video", MockVideoLayer("mixed_video"), (150, 100, 120)),  # Mixed colors
    ]

    args = InterpreterArgs(hype=50, allow_rainbows=True, min_hype=0, max_hype=100)

    for video_name, video_layer, base_color in test_videos:
        print(f"\n🎬 {video_name} (base: RGB{base_color}):")

        video_layer.color = base_color
        interpreter = RedLighting([video_layer], args, red_intensity=2.0)

        # Track color changes
        colors_applied = []
        video_layer.set_color = lambda c: colors_applied.append(c)

        # Test with different bass levels
        bass_levels = [0.2, 0.5, 0.8, 1.0]

        for bass in bass_levels:
            frame = Frame({FrameSignal.freq_low: bass})
            scheme = ColorScheme(Color("red"), Color("black"), Color("white"))

            interpreter.step(frame, scheme)

            if colors_applied:
                lit_color = colors_applied[-1]

                # Calculate enhancement
                red_enhancement = (
                    lit_color[0] / base_color[0] if base_color[0] > 0 else 1.0
                )

                print(
                    f"   Bass {bass:.1f}: RGB{lit_color} "
                    f"(Red enhancement: {red_enhancement:.2f}x)"
                )
            else:
                print(f"   Bass {bass:.1f}: No change")


def demo_selective_lighting():
    """Demonstrate selective color enhancement"""
    print("\n" + "🎯" * 30)
    print("   SELECTIVE COLOR LIGHTING")
    print("   'Enhances specific colors in video'")
    print("🎯" * 30)

    # Test different target colors
    target_tests = [
        ("Target Red", (1.0, 0.0, 0.0)),
        ("Target Green", (0.0, 1.0, 0.0)),
        ("Target Blue", (0.0, 0.0, 1.0)),
        ("Target Yellow", (1.0, 1.0, 0.0)),
        ("Target Purple", (1.0, 0.0, 1.0)),
    ]

    # Test video with mixed colors
    video_layer = MockVideoLayer("test_video")
    args = InterpreterArgs(hype=55, allow_rainbows=True, min_hype=0, max_hype=100)

    for target_name, target_color in target_tests:
        print(f"\n🎯 {target_name}:")

        interpreter = SelectiveLighting(
            [video_layer],
            args,
            target_color=target_color,
            enhancement_factor=2.0,
            color_tolerance=0.4,
        )

        # Test with different base colors to see which get enhanced
        test_colors = [
            ("Red base", (200, 50, 50)),
            ("Green base", (50, 200, 50)),
            ("Blue base", (50, 50, 200)),
            ("White base", (200, 200, 200)),
            ("Mixed base", (150, 100, 120)),
        ]

        for color_name, base_color in test_colors:
            video_layer.color = base_color

            colors_applied = []
            video_layer.set_color = lambda c: colors_applied.append(c)

            frame = Frame({FrameSignal.freq_low: 0.7})
            scheme = ColorScheme(Color("white"), Color("black"), Color("gray"))

            interpreter.step(frame, scheme)

            if colors_applied:
                enhanced_color = colors_applied[-1]

                # Calculate total enhancement
                base_brightness = sum(base_color)
                enhanced_brightness = sum(enhanced_color)
                enhancement_ratio = (
                    enhanced_brightness / base_brightness
                    if base_brightness > 0
                    else 1.0
                )

                enhancement_indicator = "✨" if enhancement_ratio > 1.2 else "📍"
                print(
                    f"     {color_name}: {base_color} → {enhanced_color} "
                    f"{enhancement_indicator} ({enhancement_ratio:.2f}x)"
                )
            else:
                print(f"     {color_name}: No enhancement")


def demo_strobe_lighting():
    """Demonstrate strobe lighting with different triggers"""
    print("\n" + "⚡" * 30)
    print("   STROBE LIGHTING EFFECTS")
    print("⚡" * 30)

    video_layer = MockVideoLayer("strobe_video")
    video_layer.color = (100, 100, 100)  # Gray base

    args = InterpreterArgs(hype=80, allow_rainbows=True, min_hype=0, max_hype=100)
    interpreter = StrobeLighting([video_layer], args, strobe_speed=0.5)

    # Track color changes over time
    print("\n⚡ Strobe Color Sequence:")

    # Manual strobe test
    frame_manual = Frame({FrameSignal.strobe: 1.0, FrameSignal.freq_all: 0.3})
    scheme = ColorScheme(Color("red"), Color("green"), Color("blue"))

    colors_sequence = []
    for i in range(15):  # 15 frames of strobe
        colors_applied = []
        video_layer.set_color = lambda c: colors_applied.append(c)

        interpreter.step(frame_manual, scheme)

        if colors_applied:
            colors_sequence.append(colors_applied[-1])

        # Print every 3rd frame to show sequence
        if i % 3 == 0:
            current_color = interpreter.strobe_colors[interpreter.current_color_index]
            color_name = _get_simple_color_name(current_color)
            print(f"   Frame {i:2d}: {color_name} {current_color}")

    print(f"\n   Total color changes: {len(set(colors_sequence))}")


def demo_channel_separation():
    """Demonstrate color channel separation"""
    print("\n" + "🌈" * 30)
    print("   COLOR CHANNEL SEPARATION")
    print("   'Bass→Red, Mid→Green, Treble→Blue'")
    print("🌈" * 30)

    video_layer = MockVideoLayer("channel_video")
    video_layer.color = (128, 128, 128)  # Neutral gray base

    args = InterpreterArgs(hype=70, allow_rainbows=True, min_hype=0, max_hype=100)
    interpreter = ColorChannelSeparation([video_layer], args, separation_intensity=2.0)

    # Test different frequency combinations
    frequency_tests = [
        (
            "🔴 Bass Only",
            {
                FrameSignal.freq_low: 0.9,
                FrameSignal.freq_all: 0.1,
                FrameSignal.freq_high: 0.1,
            },
        ),
        (
            "🟢 Mid Only",
            {
                FrameSignal.freq_low: 0.1,
                FrameSignal.freq_all: 0.9,
                FrameSignal.freq_high: 0.1,
            },
        ),
        (
            "🔵 Treble Only",
            {
                FrameSignal.freq_low: 0.1,
                FrameSignal.freq_all: 0.1,
                FrameSignal.freq_high: 0.9,
            },
        ),
        (
            "🟡 Bass + Mid",
            {
                FrameSignal.freq_low: 0.8,
                FrameSignal.freq_all: 0.8,
                FrameSignal.freq_high: 0.1,
            },
        ),
        (
            "🟣 Bass + Treble",
            {
                FrameSignal.freq_low: 0.8,
                FrameSignal.freq_all: 0.1,
                FrameSignal.freq_high: 0.8,
            },
        ),
        (
            "⚪ All Frequencies",
            {
                FrameSignal.freq_low: 0.8,
                FrameSignal.freq_all: 0.8,
                FrameSignal.freq_high: 0.8,
            },
        ),
    ]

    scheme = ColorScheme(Color("white"), Color("gray"), Color("black"))

    for test_name, signals in frequency_tests:
        # Reset base color
        video_layer.color = (128, 128, 128)

        colors_applied = []
        video_layer.set_color = lambda c: colors_applied.append(c)

        frame = Frame(signals)
        interpreter.step(frame, scheme)

        if colors_applied:
            separated_color = colors_applied[-1]
            base_color = (128, 128, 128)

            # Show channel enhancements
            r_mult = separated_color[0] / base_color[0]
            g_mult = separated_color[1] / base_color[1]
            b_mult = separated_color[2] / base_color[2]

            print(f"   {test_name}: RGB{separated_color}")
            print(
                f"      Channel multipliers: R×{r_mult:.2f} G×{g_mult:.2f} B×{b_mult:.2f}"
            )
        else:
            print(f"   {test_name}: No change")


def demo_spotlight_movement():
    """Demonstrate moving spotlight effects"""
    print("\n" + "💡" * 30)
    print("   MOVING SPOTLIGHT EFFECTS")
    print("💡" * 30)

    video_layer = MockVideoLayer("spotlight_video")
    args = InterpreterArgs(hype=65, allow_rainbows=True, min_hype=0, max_hype=100)

    interpreter = SpotlightEffect(
        [video_layer], args, num_spots=3, spot_size_range=(0.1, 0.25)
    )

    scheme = ColorScheme(Color("white"), Color("red"), Color("blue"))

    print(f"\n💡 Tracking {interpreter.num_spots} spotlights over time:")
    print("   Position format: (x, y, size, intensity)")

    # Simulate movement over time with different audio
    audio_scenarios = [
        ("Low energy", 0.2, 0.1),
        ("Building", 0.5, 0.3),
        ("Peak energy", 0.9, 0.8),
        ("Breakdown", 0.3, 0.7),
    ]

    for scenario_name, bass, treble in audio_scenarios:
        frame = Frame(
            {
                FrameSignal.freq_low: bass,
                FrameSignal.freq_high: treble,
                FrameSignal.freq_all: (bass + treble) / 2,
            }
        )

        interpreter.step(frame, scheme)

        print(f"\n   🎵 {scenario_name} (bass:{bass:.1f}, treble:{treble:.1f}):")

        spotlight_info = interpreter.get_spotlight_info()
        for i, spot in enumerate(spotlight_info):
            print(
                f"      Spot {i+1}: ({spot['x']:.2f}, {spot['y']:.2f}, "
                f"{spot['size']:.3f}, {spot['intensity']:.2f}) "
                f"[{spot['movement_pattern']}]"
            )


def demo_warm_cool_temperature():
    """Demonstrate warm/cool lighting temperature effects"""
    print("\n" + "🌡️" * 30)
    print("   WARM/COOL TEMPERATURE LIGHTING")
    print("   'Bass = Warm, Treble = Cool'")
    print("🌡️" * 30)

    video_layer = MockVideoLayer("temperature_video")
    video_layer.color = (128, 128, 128)  # Neutral base

    args = InterpreterArgs(hype=35, allow_rainbows=True, min_hype=0, max_hype=100)
    interpreter = WarmCoolLighting([video_layer], args)

    # Test temperature scenarios
    temperature_tests = [
        ("🔥 Very Warm (High Bass)", 0.9, 0.1),
        ("🌡️ Warm", 0.7, 0.3),
        ("⚖️ Neutral", 0.5, 0.5),
        ("❄️ Cool", 0.3, 0.7),
        ("🧊 Very Cool (High Treble)", 0.1, 0.9),
    ]

    scheme = ColorScheme(Color("orange"), Color("blue"), Color("white"))

    for temp_name, bass, treble in temperature_tests:
        # Reset color
        video_layer.color = (128, 128, 128)

        colors_applied = []
        video_layer.set_color = lambda c: colors_applied.append(c)

        frame = Frame({FrameSignal.freq_low: bass, FrameSignal.freq_high: treble})
        interpreter.step(frame, scheme)

        if colors_applied:
            temp_color = colors_applied[-1]

            # Analyze temperature
            red_ratio = temp_color[0] / 128.0
            blue_ratio = temp_color[2] / 128.0
            warmth = red_ratio - blue_ratio  # Positive = warm, negative = cool

            temp_indicator = "🔥" if warmth > 0.2 else "❄️" if warmth < -0.2 else "🌡️"
            print(
                f"   {temp_name}: RGB{temp_color} "
                f"{temp_indicator} (warmth: {warmth:+.2f})"
            )
        else:
            print(f"   {temp_name}: No change")


def _get_simple_color_name(color_tuple):
    """Get simple color name for display"""
    r, g, b = color_tuple

    if r > 200 and g < 100 and b < 100:
        return "Red"
    elif g > 200 and r < 100 and b < 100:
        return "Green"
    elif b > 200 and r < 100 and g < 100:
        return "Blue"
    elif r > 200 and g > 150 and b < 100:
        return "Orange"
    elif r > 150 and g < 100 and b > 150:
        return "Purple"
    elif r > 200 and g > 200 and b > 200:
        return "White"
    elif r < 50 and g < 50 and b < 50:
        return "Black"
    else:
        return "Mixed"


def main():
    """Run all color lighting demos"""
    try:
        demo_color_lighting_effects()
        demo_red_lighting_showcase()
        demo_selective_lighting()
        demo_strobe_lighting()
        demo_channel_separation()
        demo_spotlight_movement()
        demo_warm_cool_temperature()

        print("\n" + "🎨" * 40)
        print("  COLOR LIGHTING SYSTEM COMPLETE!")
        print("🎨" * 40)
        print("\n✨ Features demonstrated:")
        print("   🔴 Red lighting picks out red/white video content")
        print("   🔵 Blue lighting enhances blue/cyan areas")
        print("   🎯 Selective lighting targets specific colors")
        print("   ⚡ Strobe lighting with color cycling")
        print("   🌈 Channel separation (bass→red, treble→blue)")
        print("   💡 Moving spotlights with audio tracking")
        print("   🌡️ Warm/cool temperature shifts")
        print("   🔦 Color scheme integration")
        print("\n🎬 These effects will make your videos pop with color!")
        print("   Use them in gentle mode for subtle enhancement")
        print("   Use them in rave mode for dramatic color effects")

    except Exception as e:
        print(f"Demo failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
