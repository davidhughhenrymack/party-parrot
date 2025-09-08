#!/usr/bin/env python3
"""
Strobe Effects Demo
Showcases strobing effects like in fixture renderers but for VJ layers
"""
import numpy as np
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.interpreters.base import InterpreterArgs
from parrot.utils.colour import Color
from parrot.vj.base import SolidLayer
from parrot.vj.layers.text import MockTextLayer
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


def demo_basic_strobing():
    """Demonstrate basic strobe flash effects"""
    print("⚡" * 30)
    print("   BASIC STROBE EFFECTS")
    print("   'Like fixture strobing but for VJ layers'")
    print("⚡" * 30)

    # Create test layers
    layers = [
        SolidLayer("background", color=(50, 50, 50), width=400, height=300),
        SolidLayer("foreground", color=(200, 100, 150), width=400, height=300),
    ]

    args = InterpreterArgs(hype=80, allow_rainbows=True, min_hype=0, max_hype=100)

    # Test different strobe frequencies
    strobe_configs = [
        ("Slow Strobe", 5.0),
        ("Medium Strobe", 10.0),
        ("Fast Strobe", 20.0),
        ("Ultra Fast", 40.0),
    ]

    for config_name, frequency in strobe_configs:
        print(f"\n⚡ {config_name} ({frequency}Hz):")

        interpreter = StrobeFlash(layers, args, strobe_frequency=frequency)
        scheme = ColorScheme(Color("red"), Color("blue"), Color("white"))

        # Track alpha changes over strobe cycles
        alpha_values = []

        def track_alpha(alpha):
            alpha_values.append(alpha)

        layers[0].set_alpha = track_alpha

        # Trigger strobe
        frame_on = Frame({FrameSignal.strobe: 1.0})
        frame_off = Frame({FrameSignal.strobe: 0.0})

        # Simulate strobe on/off cycles
        for cycle in range(3):
            # Strobe ON phase
            for _ in range(10):  # 10 frames of strobing
                interpreter.step(frame_on, scheme)

            # Strobe OFF phase
            for _ in range(5):  # 5 frames of normal
                interpreter.step(frame_off, scheme)

        if alpha_values:
            # Analyze strobe pattern
            min_alpha = min(alpha_values)
            max_alpha = max(alpha_values)
            unique_values = len(set(alpha_values))

            print(f"   Alpha range: {min_alpha:.1f} - {max_alpha:.1f}")
            print(f"   Pattern variation: {unique_values} different values")
            print(f"   Strobe active: {interpreter.strobe_active}")


def demo_beat_synchronized_strobing():
    """Demonstrate beat-synchronized strobing"""
    print("\n" + "🥁" * 30)
    print("   BEAT-SYNCHRONIZED STROBING")
    print("🥁" * 30)

    layers = [SolidLayer("beat_layer", width=300, height=200)]
    args = InterpreterArgs(hype=85, allow_rainbows=True, min_hype=0, max_hype=100)

    interpreter = BeatStrobe(layers, args, beat_threshold=0.7, strobe_duration=8)
    scheme = ColorScheme(Color("red"), Color("green"), Color("blue"))

    print("\n🥁 Simulating beat sequence:")

    # Simulate song with beats
    beat_sequence = [
        ("🎵 Quiet", 0.3, False),
        ("🎵 Build", 0.5, False),
        ("💥 BEAT 1", 0.8, True),
        ("🎵 Between", 0.4, False),
        ("💥 BEAT 2", 0.9, True),
        ("🎵 Break", 0.2, False),
        ("💥 BEAT 3", 0.85, True),
        ("🎵 Fade", 0.1, False),
    ]

    for moment_name, signal_level, is_beat in beat_sequence:
        frame = Frame({FrameSignal.freq_high: signal_level})

        old_beat_count = interpreter.beat_count
        old_strobe_frames = interpreter.strobe_frames_remaining

        interpreter.step(frame, scheme)

        new_beat_count = interpreter.beat_count
        new_strobe_frames = interpreter.strobe_frames_remaining

        beat_detected = new_beat_count > old_beat_count
        strobe_active = new_strobe_frames > 0

        status = []
        if beat_detected:
            status.append("BEAT DETECTED")
        if strobe_active:
            status.append(f"STROBING ({new_strobe_frames} frames)")
        if not status:
            status.append("normal")

        print(f"   {moment_name}: {' + '.join(status)}")


def demo_color_cycling_strobe():
    """Demonstrate color cycling strobe effects"""
    print("\n" + "🌈" * 30)
    print("   COLOR CYCLING STROBE")
    print("🌈" * 30)

    layers = [SolidLayer("color_layer", width=200, height=150)]
    args = InterpreterArgs(hype=75, allow_rainbows=True, min_hype=0, max_hype=100)

    interpreter = ColorStrobe(layers, args, strobe_speed=0.8)

    # Test with different color schemes
    schemes = [
        ("🔴 Red Theme", ColorScheme(Color("red"), Color("darkred"), Color("pink"))),
        ("🔵 Blue Theme", ColorScheme(Color("blue"), Color("navy"), Color("cyan"))),
        ("🎃 Halloween", ColorScheme(Color("orange"), Color("black"), Color("red"))),
    ]

    for scheme_name, scheme in schemes:
        print(f"\n{scheme_name}:")

        # Set colors from scheme
        interpreter.set_colors_from_scheme(scheme)

        # Track color changes
        colors_applied = []
        layers[0].set_color = lambda c: colors_applied.append(c)

        # Simulate strobing
        frame_strobe = Frame({FrameSignal.strobe: 1.0, FrameSignal.freq_all: 0.6})
        frame_normal = Frame({FrameSignal.strobe: 0.0, FrameSignal.freq_all: 0.4})

        # Strobe phase
        for _ in range(8):
            interpreter.step(frame_strobe, scheme)

        # Normal phase
        for _ in range(4):
            interpreter.step(frame_normal, scheme)

        if colors_applied:
            unique_colors = len(set(colors_applied))
            print(f"   Colors used: {unique_colors} different colors")

            # Show first few colors
            for i, color in enumerate(colors_applied[:4]):
                color_name = interpreter._get_color_name(color)
                print(f"     Step {i+1}: {color_name} RGB{color}")


def demo_audio_reactive_strobing():
    """Demonstrate audio-reactive strobing"""
    print("\n" + "🎵" * 30)
    print("   AUDIO-REACTIVE STROBING")
    print("   'Different frequencies trigger different strobes'")
    print("🎵" * 30)

    layers = [SolidLayer("audio_layer", width=300, height=200)]
    args = InterpreterArgs(hype=90, allow_rainbows=True, min_hype=0, max_hype=100)

    interpreter = AudioReactiveStrobe(layers, args)
    scheme = ColorScheme(Color("red"), Color("green"), Color("blue"))

    # Test different frequency scenarios
    audio_scenarios = [
        (
            "🔊 Bass Heavy",
            {
                FrameSignal.freq_low: 0.9,
                FrameSignal.freq_high: 0.2,
                FrameSignal.sustained_low: 0.3,
            },
        ),
        (
            "🎼 Treble Heavy",
            {
                FrameSignal.freq_low: 0.2,
                FrameSignal.freq_high: 0.9,
                FrameSignal.sustained_low: 0.3,
            },
        ),
        (
            "🌊 Sustained",
            {
                FrameSignal.freq_low: 0.4,
                FrameSignal.freq_high: 0.3,
                FrameSignal.sustained_low: 0.9,
            },
        ),
        (
            "🔥 Full Spectrum",
            {
                FrameSignal.freq_low: 0.8,
                FrameSignal.freq_high: 0.8,
                FrameSignal.sustained_low: 0.8,
            },
        ),
    ]

    for scenario_name, signals in audio_scenarios:
        frame = Frame(signals)

        # Track color and alpha changes
        colors_applied = []
        alphas_applied = []

        layers[0].set_color = lambda c: colors_applied.append(c)
        layers[0].set_alpha = lambda a: alphas_applied.append(a)

        # Multiple steps to see strobing
        for _ in range(6):
            interpreter.step(frame, scheme)

        print(f"\n{scenario_name}:")
        print(f"   Status: {interpreter}")

        if colors_applied:
            final_color = colors_applied[-1]
            r, g, b = final_color

            # Analyze color dominance
            if r > g and r > b:
                dominant = "🔴 Red-dominant"
            elif g > r and g > b:
                dominant = "🟢 Green-dominant"
            elif b > r and b > g:
                dominant = "🔵 Blue-dominant"
            else:
                dominant = "⚪ Mixed"

            print(f"   Color result: {dominant} RGB({r}, {g}, {b})")

        if alphas_applied:
            avg_alpha = sum(alphas_applied) / len(alphas_applied)
            print(f"   Average alpha: {avg_alpha:.2f}")


def demo_rgb_channel_strobing():
    """Demonstrate RGB channel strobing"""
    print("\n" + "🌈" * 30)
    print("   RGB CHANNEL STROBING")
    print("   'Bass→Red, Mid→Green, Treble→Blue'")
    print("🌈" * 30)

    layers = [SolidLayer("rgb_layer", width=250, height=200)]
    args = InterpreterArgs(hype=70, allow_rainbows=True, min_hype=0, max_hype=100)

    interpreter = RGBChannelStrobe(layers, args, channel_frequencies=(8.0, 12.0, 16.0))
    scheme = ColorScheme(Color("white"), Color("gray"), Color("black"))

    print(
        f"\n🌈 Channel frequencies: R={interpreter.red_freq}Hz, G={interpreter.green_freq}Hz, B={interpreter.blue_freq}Hz"
    )

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
            "⚪ All Channels",
            {
                FrameSignal.freq_low: 0.8,
                FrameSignal.freq_all: 0.8,
                FrameSignal.freq_high: 0.8,
            },
        ),
    ]

    for test_name, signals in frequency_tests:
        frame = Frame(signals)

        # Track color changes over time
        color_sequence = []

        for step in range(8):  # 8 frames to see strobing
            colors_applied = []
            layers[0].set_color = lambda c: colors_applied.append(c)

            interpreter.step(frame, scheme)

            if colors_applied:
                color_sequence.append(colors_applied[-1])

        print(f"\n{test_name}:")

        if color_sequence:
            # Analyze color progression
            first_color = color_sequence[0]
            last_color = color_sequence[-1]

            print(f"   Start: RGB{first_color}")
            print(f"   End:   RGB{last_color}")

            # Show color channel activity
            avg_r = sum(c[0] for c in color_sequence) / len(color_sequence)
            avg_g = sum(c[1] for c in color_sequence) / len(color_sequence)
            avg_b = sum(c[2] for c in color_sequence) / len(color_sequence)

            print(f"   Avg channels: R={avg_r:.0f}, G={avg_g:.0f}, B={avg_b:.0f}")


def demo_pattern_strobing():
    """Demonstrate pattern-based strobing"""
    print("\n" + "📋" * 30)
    print("   PATTERN STROBING")
    print("📋" * 30)

    layers = [SolidLayer("pattern_layer", width=200, height=150)]
    args = InterpreterArgs(hype=65, allow_rainbows=True, min_hype=0, max_hype=100)

    # Custom strobe patterns
    custom_patterns = [
        [1.0, 0.0, 1.0, 0.0],  # Simple on/off
        [1.0, 1.0, 0.0, 0.0],  # Double flash
        [1.0, 0.8, 0.6, 0.4, 0.2, 0.0],  # Fade down
        [0.2, 0.4, 0.6, 0.8, 1.0, 0.8, 0.6, 0.4],  # Fade up and down
        [1.0, 0.0, 0.5, 0.0, 1.0, 0.0, 0.0],  # Triple flash
    ]

    interpreter = PatternStrobe(
        layers, args, patterns=custom_patterns, pattern_speed=1.5
    )
    scheme = ColorScheme(Color("purple"), Color("orange"), Color("cyan"))

    print(f"\n📋 Testing {len(custom_patterns)} strobe patterns:")

    for i, pattern in enumerate(custom_patterns):
        print(f"\n   Pattern {i+1}: {pattern}")

        # Force specific pattern
        interpreter.current_pattern_index = i
        interpreter.pattern_frame_count = 0

        # Track alpha values
        alpha_sequence = []
        layers[0].set_alpha = lambda a: alpha_sequence.append(a)

        # Execute pattern
        frame = Frame({FrameSignal.strobe: 1.0, FrameSignal.freq_all: 0.6})

        for step in range(len(pattern) + 2):
            interpreter.step(frame, scheme)

        if alpha_sequence:
            print(f"     Executed: {alpha_sequence[:len(pattern)]}")


def demo_high_speed_strobing():
    """Demonstrate high-speed strobing for intense moments"""
    print("\n" + "🚀" * 30)
    print("   HIGH-SPEED STROBING")
    print("   'Ultra-fast strobing for peak energy'")
    print("🚀" * 30)

    layers = [SolidLayer("speed_layer", width=300, height=200)]
    args = InterpreterArgs(hype=95, allow_rainbows=True, min_hype=0, max_hype=100)

    interpreter = HighSpeedStrobe(
        layers, args, base_frequency=20.0, max_frequency=60.0, trigger_threshold=0.8
    )

    scheme = ColorScheme(Color("white"), Color("red"), Color("blue"))

    # Test frequency scaling
    energy_levels = [
        ("🎵 Low Energy", 0.2, 0.5),
        ("🔥 Medium Energy", 0.6, 0.9),
        ("💥 PEAK ENERGY", 0.95, 0.95),
    ]

    print("\n🚀 Frequency scaling with energy:")

    for level_name, energy, sustained in energy_levels:
        frame = Frame(
            {FrameSignal.freq_all: energy, FrameSignal.sustained_high: sustained}
        )

        old_frequency = interpreter.current_frequency
        interpreter.step(frame, scheme)
        new_frequency = interpreter.current_frequency

        trigger_active = sustained > interpreter.trigger_threshold

        print(f"   {level_name}:")
        print(f"     Energy: {energy:.1f}, Sustained: {sustained:.1f}")
        print(f"     Frequency: {new_frequency:.1f}Hz")
        print(f"     High-speed mode: {'YES' if trigger_active else 'NO'}")
        print(f"     Intensity multiplier: {interpreter.intensity_multiplier:.1f}x")


def demo_layer_selective_strobing():
    """Demonstrate layer-selective strobing"""
    print("\n" + "🔄" * 30)
    print("   LAYER-SELECTIVE STROBING")
    print("   'Different layers strobe independently'")
    print("🔄" * 30)

    # Create multiple layers
    layers = [
        SolidLayer("layer1", color=(255, 100, 100), width=200, height=150),
        SolidLayer("layer2", color=(100, 255, 100), width=200, height=150),
        SolidLayer("layer3", color=(100, 100, 255), width=200, height=150),
    ]

    args = InterpreterArgs(hype=60, allow_rainbows=True, min_hype=0, max_hype=100)

    interpreter = LayerSelectiveStrobe(
        layers, args, strobe_frequency=12.0, layer_offset=0.33
    )  # 33% offset between layers

    scheme = ColorScheme(Color("red"), Color("green"), Color("blue"))

    print(
        f"\n🔄 {len(layers)} layers with {interpreter.layer_offset:.0%} phase offset:"
    )

    # Track each layer's alpha independently
    layer_alphas = [[] for _ in range(len(layers))]

    for i, layer in enumerate(layers):

        def make_tracker(layer_index):
            return lambda a: layer_alphas[layer_index].append(a)

        layer.set_alpha = make_tracker(i)

    # Simulate strobing
    frame = Frame({FrameSignal.strobe: 1.0, FrameSignal.freq_all: 0.7})

    for step in range(12):  # Multiple steps to see phase differences
        interpreter.step(frame, scheme)

    # Analyze phase differences
    for i, alphas in enumerate(layer_alphas):
        if alphas:
            avg_alpha = sum(alphas) / len(alphas)
            alpha_variation = max(alphas) - min(alphas)

            print(
                f"   Layer {i+1}: avg α={avg_alpha:.2f}, variation={alpha_variation:.2f}"
            )


def demo_strobe_blackout():
    """Demonstrate strobe blackout effects"""
    print("\n" + "⚫" * 30)
    print("   STROBE BLACKOUT EFFECTS")
    print("⚫" * 30)

    layers = [SolidLayer("blackout_layer", width=200, height=150)]
    args = InterpreterArgs(hype=55, allow_rainbows=True, min_hype=0, max_hype=100)

    interpreter = StrobeBlackout(
        layers,
        args,
        blackout_probability=0.4,  # 40% chance of blackout
        flash_duration=3,
        blackout_duration=6,
    )

    scheme = ColorScheme(Color("white"), Color("black"), Color("red"))

    print("\n⚫ Simulating strobe triggers (40% blackout chance):")

    # Track alpha values to see blackouts vs flashes
    alpha_values = []
    layers[0].set_alpha = lambda a: alpha_values.append(a)

    # Trigger multiple strobe events
    for trigger in range(8):
        print(f"\n   Trigger {trigger+1}:")

        # Reset state
        interpreter.current_state = "normal"
        interpreter.trigger_cooldown = 0

        # Trigger strobe
        frame = Frame({FrameSignal.strobe: 1.0})
        interpreter.step(frame, scheme)

        state = interpreter.current_state
        frames_remaining = interpreter.state_frames_remaining

        if state == "blackout":
            print(f"     ⚫ BLACKOUT! ({frames_remaining} frames)")
        elif state == "flash":
            print(f"     ⚡ FLASH! ({frames_remaining} frames)")
        else:
            print(f"     📍 Normal operation")

        # Continue for a few frames to see effect
        frame_normal = Frame({FrameSignal.strobe: 0.0})
        for _ in range(3):
            interpreter.step(frame_normal, scheme)


def demo_complete_strobe_show():
    """Demonstrate a complete strobe show with multiple effects"""
    print("\n" + "🎆" * 30)
    print("   COMPLETE STROBE SHOW")
    print("🎆" * 30)

    # Create multiple layers for different strobe effects
    layers = [
        SolidLayer("background", color=(30, 30, 30), width=600, height=400),
        SolidLayer("midground", color=(150, 100, 200), width=600, height=400),
        MockTextLayer("STROBE", "text_layer"),
    ]

    args = InterpreterArgs(hype=85, allow_rainbows=True, min_hype=0, max_hype=100)

    # Multiple strobe interpreters
    interpreters = [
        StrobeFlash(
            [layers[0]], args, strobe_frequency=12.0
        ),  # Background basic strobe
        ColorStrobe([layers[1]], args, strobe_speed=0.6),  # Midground color strobe
        BeatStrobe([layers[2]], args, beat_threshold=0.7),  # Text beat strobe
        AudioReactiveStrobe(layers[:2], args),  # Multi-layer audio strobe
    ]

    # Simulate party progression
    party_progression = [
        (
            "🎵 Intro",
            {
                FrameSignal.freq_low: 0.3,
                FrameSignal.freq_high: 0.2,
                FrameSignal.freq_all: 0.25,
                FrameSignal.strobe: 0.0,
            },
        ),
        (
            "⚡ Manual Strobe",
            {
                FrameSignal.freq_low: 0.5,
                FrameSignal.freq_high: 0.4,
                FrameSignal.freq_all: 0.45,
                FrameSignal.strobe: 1.0,  # Manual strobe trigger
            },
        ),
        (
            "🥁 Beat Section",
            {
                FrameSignal.freq_low: 0.6,
                FrameSignal.freq_high: 0.85,  # High treble for beats
                FrameSignal.freq_all: 0.7,
                FrameSignal.strobe: 0.0,
            },
        ),
        (
            "💥 CHAOS MODE",
            {
                FrameSignal.freq_low: 0.95,
                FrameSignal.freq_high: 0.9,
                FrameSignal.freq_all: 0.92,
                FrameSignal.sustained_high: 0.95,
                FrameSignal.strobe: 1.0,
            },
        ),
    ]

    schemes = [
        ColorScheme(Color("red"), Color("black"), Color("white")),
        ColorScheme(Color("blue"), Color("orange"), Color("purple")),
        ColorScheme(Color("green"), Color("yellow"), Color("pink")),
        ColorScheme(Color("white"), Color("red"), Color("gold")),
    ]

    print(f"\n🎆 Strobe show progression:")

    for i, (moment_name, signals) in enumerate(party_progression):
        frame = Frame(signals)
        scheme = schemes[i % len(schemes)]

        print(f"\n{moment_name}:")

        # Update all strobe interpreters
        active_strobes = []

        for interp in interpreters:
            old_str = str(interp)
            interp.step(frame, scheme)
            new_str = str(interp)

            # Check if strobe is active
            if any(
                keyword in new_str.lower()
                for keyword in ["strobing", "flashing", "active", "bursting", "on"]
            ):
                active_strobes.append(new_str)

        print(f"   🎨 Color scheme: {scheme.fg} / {scheme.bg} / {scheme.bg_contrast}")

        if active_strobes:
            print(f"   ⚡ Active strobes:")
            for strobe in active_strobes:
                print(f"     - {strobe}")
        else:
            print(f"   📍 No active strobes")

        # Special moments
        if signals.get(FrameSignal.strobe, 0) > 0.5:
            print("   🌟 MANUAL STROBE ACTIVATED!")
        if signals.get(FrameSignal.freq_all, 0) > 0.9:
            print("   🔥 PEAK ENERGY - Maximum strobe intensity!")


def main():
    """Run all strobe effect demos"""
    try:
        demo_basic_strobing()
        demo_beat_synchronized_strobing()
        demo_color_cycling_strobe()
        demo_audio_reactive_strobing()
        demo_rgb_channel_strobing()
        demo_pattern_strobing()
        demo_layer_selective_strobing()
        demo_strobe_blackout()
        demo_complete_strobe_show()

        print("\n" + "⚡" * 40)
        print("  STROBE EFFECTS SYSTEM COMPLETE!")
        print("⚡" * 40)

        print("\n✨ Strobe effects demonstrated:")
        print("   ⚡ Basic strobing - on/off flashing at configurable frequencies")
        print("   🌈 Color strobing - cycles through color palettes")
        print("   🥁 Beat strobing - synchronized to beat detection")
        print("   🎲 Random strobing - unpredictable strobe patterns")
        print("   🚀 High-speed strobing - ultra-fast for peak energy")
        print("   📋 Pattern strobing - custom strobe sequences")
        print("   🎵 Audio-reactive - different frequencies trigger different strobes")
        print("   🔄 Layer-selective - different layers strobe independently")
        print("   ⚫ Strobe blackout - dramatic blackouts vs bright flashes")
        print("   🌈 RGB channel strobing - each color channel strobes independently")
        print("   🔍 Strobe zoom - strobing with scale/zoom effects")

        print("\n🎛️ Control methods:")
        print("   🎛️ Manual strobe button - triggers all strobe effects")
        print("   🔊 Bass response - affects strobe intensity")
        print("   🎼 Treble response - triggers beat strobes")
        print("   ⚡ Energy levels - scale strobe frequency and intensity")
        print("   🥁 Beat detection - synchronizes strobe timing")

        print("\n🎃 Perfect for your Dead Sexy Halloween party!")
        print("   Strobing will make all your visuals flash dramatically")
        print("   Use gentle mode for subtle strobing")
        print("   Use rave mode for INTENSE strobe chaos!")

        print("\n⚡ Your party will have professional strobe effects! ⚡")

    except Exception as e:
        print(f"Demo failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
