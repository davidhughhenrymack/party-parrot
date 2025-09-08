#!/usr/bin/env python3
"""
Concert-Style Laser Show Demo
Showcases laser effects that fan out and respond to audio like in concerts
"""
import math
import numpy as np
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.interpreters.base import InterpreterArgs
from parrot.utils.colour import Color
from parrot.vj.layers.laser import LaserLayer, LaserHaze, LaserBeamRenderer
from parrot.vj.interpreters.laser_effects import (
    ConcertLasers,
    LaserScan,
    LaserMatrix,
    LaserChase,
    LaserBurst,
    LaserSpiral,
)


def demo_concert_laser_fan():
    """Demonstrate concert-style fanned laser beams"""
    print("🔴" * 30)
    print("   CONCERT LASER FAN DEMO")
    print("   'Lasers fan out like in concerts'")
    print("🔴" * 30)

    # Create laser layer and interpreter
    laser_layer = LaserLayer("concert_lasers", width=800, height=600, beam_glow=True)
    args = InterpreterArgs(hype=75, allow_rainbows=True, min_hype=0, max_hype=100)

    # Test different fan configurations
    fan_configs = [
        ("Narrow Fan", 4, 60.0),  # 4 lasers, 60° spread
        ("Wide Fan", 8, 120.0),  # 8 lasers, 120° spread
        ("Super Wide", 12, 180.0),  # 12 lasers, 180° spread
        ("Mega Fan", 16, 240.0),  # 16 lasers, 240° spread (overlapping)
    ]

    for config_name, num_lasers, fan_angle in fan_configs:
        print(f"\n🎯 {config_name} ({num_lasers} lasers, {fan_angle}°):")

        interpreter = ConcertLasers(
            [laser_layer],
            args,
            num_lasers=num_lasers,
            fan_angle=fan_angle,
            origin_point=(0.5, 0.85),
        )  # Slightly higher origin

        # Test with different audio scenarios
        scenarios = [
            (
                "🎵 Ambient",
                Frame(
                    {
                        FrameSignal.freq_low: 0.3,
                        FrameSignal.freq_high: 0.2,
                        FrameSignal.freq_all: 0.25,
                        FrameSignal.sustained_low: 0.4,
                    }
                ),
            ),
            (
                "🔥 Drop Hit",
                Frame(
                    {
                        FrameSignal.freq_low: 0.95,
                        FrameSignal.freq_high: 0.9,
                        FrameSignal.freq_all: 0.92,
                        FrameSignal.sustained_low: 0.9,
                    }
                ),
            ),
        ]

        schemes = [
            ColorScheme(Color("red"), Color("blue"), Color("white")),
            ColorScheme(Color("green"), Color("purple"), Color("orange")),
        ]

        for scenario_name, frame in scenarios:
            for i, scheme in enumerate(schemes):
                interpreter.step(frame, scheme)

                # Get laser info
                laser_info = interpreter.get_laser_info()
                active_lasers = len(laser_info)

                if laser_info:
                    avg_intensity = sum(
                        laser["intensity"] for laser in laser_info
                    ) / len(laser_info)

                    # Get color info
                    colors = [laser["color"] for laser in laser_info]
                    unique_colors = len(set(colors))

                    print(
                        f"     {scenario_name} (scheme {i+1}): "
                        f"{active_lasers} beams active, "
                        f"avg intensity {avg_intensity:.2f}, "
                        f"{unique_colors} colors"
                    )

                    # Show beam angles for first few lasers
                    if active_lasers <= 4:
                        angles_deg = [
                            math.degrees(laser["current_angle"]) for laser in laser_info
                        ]
                        print(
                            f"       Beam angles: {[f'{a:.0f}°' for a in angles_deg]}"
                        )
                else:
                    print(f"     {scenario_name}: No active lasers")


def demo_laser_matrix_patterns():
    """Demonstrate laser matrix grid patterns"""
    print("\n" + "🔳" * 30)
    print("   LASER MATRIX PATTERNS")
    print("🔳" * 30)

    laser_layer = LaserLayer("matrix_lasers", width=600, height=400)
    args = InterpreterArgs(hype=85, allow_rainbows=True, min_hype=0, max_hype=100)

    # Test different grid sizes
    grid_configs = [
        ("Small Grid", (4, 3)),
        ("Medium Grid", (6, 4)),
        ("Large Grid", (8, 6)),
        ("Wide Grid", (10, 3)),
    ]

    for config_name, grid_size in grid_configs:
        print(f"\n🔳 {config_name} ({grid_size[0]}×{grid_size[1]}):")

        interpreter = LaserMatrix(
            [laser_layer], args, grid_size=grid_size, pulse_speed=0.1
        )

        scheme = ColorScheme(Color("cyan"), Color("magenta"), Color("yellow"))

        # Test wave progression
        audio_progression = [
            ("Low", 0.2, 0.1, 0.15),
            ("Med", 0.5, 0.4, 0.45),
            ("High", 0.8, 0.7, 0.75),
        ]

        for energy_name, bass, treble, energy in audio_progression:
            frame = Frame(
                {
                    FrameSignal.freq_low: bass,
                    FrameSignal.freq_high: treble,
                    FrameSignal.freq_all: energy,
                }
            )

            interpreter.step(frame, scheme)

            matrix_info = interpreter.get_matrix_info()
            grid = matrix_info["grid"]

            # Count active points
            active_points = sum(1 for row in grid for laser in row if laser["enabled"])
            total_points = grid_size[0] * grid_size[1]

            # Average intensity
            total_intensity = sum(laser["intensity"] for row in grid for laser in row)
            avg_intensity = total_intensity / total_points

            print(
                f"     {energy_name} energy: {active_points}/{total_points} active, "
                f"avg intensity {avg_intensity:.2f}"
            )


def demo_laser_chase_effects():
    """Demonstrate chasing laser effects"""
    print("\n" + "🏃" * 30)
    print("   LASER CHASE EFFECTS")
    print("🏃" * 30)

    laser_layer = LaserLayer("chase_lasers", width=500, height=400)
    args = InterpreterArgs(hype=70, allow_rainbows=True, min_hype=0, max_hype=100)

    interpreter = LaserChase(
        [laser_layer], args, num_chasers=6, chase_speed=0.15, trail_length=4
    )

    scheme = ColorScheme(Color("red"), Color("green"), Color("blue"))

    print(f"\n🏃 Tracking {interpreter.num_chasers} chasers with trails:")

    # Simulate beat-driven chase
    beat_sequence = [
        ("🎵 Build", 0.3, 0.2),  # No beat
        ("💥 Beat 1", 0.7, 0.8),  # Beat hit
        ("🎵 Break", 0.4, 0.3),  # Between beats
        ("💥 Beat 2", 0.8, 0.9),  # Stronger beat
        ("🎵 Fade", 0.2, 0.1),  # Energy drops
    ]

    for beat_name, bass, treble in beat_sequence:
        frame = Frame(
            {
                FrameSignal.freq_low: bass,
                FrameSignal.freq_high: treble,
                FrameSignal.freq_all: (bass + treble) / 2,
            }
        )

        old_phase = interpreter.chase_phase
        interpreter.step(frame, scheme)
        new_phase = interpreter.chase_phase

        phase_advance = new_phase - old_phase

        print(f"   {beat_name}: phase advance {phase_advance:.3f}")

        # Show chaser positions
        chase_info = interpreter.get_chase_info()
        positions = [
            f"{chaser['position']:.2f}" for chaser in chase_info[:3]
        ]  # First 3
        print(f"     Chaser positions: {positions}")


def demo_laser_burst_explosion():
    """Demonstrate explosive laser burst effects"""
    print("\n" + "💥" * 30)
    print("   LASER BURST EXPLOSIONS")
    print("💥" * 30)

    laser_layer = LaserLayer("burst_lasers", width=400, height=300)
    args = InterpreterArgs(hype=90, allow_rainbows=True, min_hype=0, max_hype=100)

    interpreter = LaserBurst(
        [laser_layer],
        args,
        burst_threshold=0.75,
        max_burst_lasers=20,
        burst_duration=15,
    )

    scheme = ColorScheme(Color("white"), Color("red"), Color("blue"))

    print("\n💥 Simulating energy spikes for burst triggers:")

    # Simulate energy progression
    energy_sequence = [
        ("🎵 Quiet", 0.2, 0.1, 0.15),
        ("🎶 Building", 0.5, 0.4, 0.45),
        ("🔥 Peak", 0.95, 0.9, 0.92),  # Should trigger burst
        ("💥 Sustain", 0.8, 0.85, 0.82),
        ("📉 Decay", 0.4, 0.3, 0.35),
        ("🔥 Second Peak", 0.98, 0.95, 0.96),  # Another burst
        ("🌑 Fade", 0.1, 0.05, 0.07),
    ]

    for moment_name, bass, treble, energy in energy_sequence:
        frame = Frame(
            {
                FrameSignal.freq_low: bass,
                FrameSignal.freq_high: treble,
                FrameSignal.freq_all: energy,
            }
        )

        interpreter.step(frame, scheme)

        burst_info = interpreter.get_burst_info()

        if burst_info["is_bursting"]:
            print(
                f"   {moment_name}: 💥 BURSTING! {len(burst_info['lasers'])} beams, "
                f"{burst_info['frames_remaining']} frames left"
            )
        else:
            print(f"   {moment_name}: Ready (energy: {energy:.2f})")


def demo_laser_spiral_patterns():
    """Demonstrate spiral laser patterns"""
    print("\n" + "🌀" * 30)
    print("   LASER SPIRAL PATTERNS")
    print("🌀" * 30)

    laser_layer = LaserLayer(
        "spiral_lasers", width=400, height=400
    )  # Square for spirals
    args = InterpreterArgs(hype=65, allow_rainbows=True, min_hype=0, max_hype=100)

    interpreter = LaserSpiral(
        [laser_layer], args, num_spirals=3, spiral_speed=0.06, spiral_tightness=3.0
    )

    scheme = ColorScheme(Color("purple"), Color("orange"), Color("cyan"))

    print(f"\n🌀 {interpreter.num_spirals} spirals spinning:")

    # Test spiral evolution over time
    for step in range(8):
        frame = Frame(
            {
                FrameSignal.freq_high: 0.6 + 0.1 * step,  # Increasing treble
                FrameSignal.freq_all: 0.5 + 0.05 * step,
            }
        )

        interpreter.step(frame, scheme)

        spiral_info = interpreter.get_spiral_info()

        print(f"   Step {step+1}: phase {interpreter.spiral_phase:.2f}")

        for i, spiral in enumerate(spiral_info):
            points_count = len(spiral["points"])
            avg_intensity = sum(p["intensity"] for p in spiral["points"]) / max(
                1, points_count
            )

            print(
                f"     Spiral {i+1}: {points_count} points, "
                f"intensity {avg_intensity:.2f}, "
                f"direction {spiral['direction']}"
            )


def demo_laser_scanning():
    """Demonstrate scanning laser effects"""
    print("\n" + "🔍" * 30)
    print("   LASER SCANNING EFFECTS")
    print("🔍" * 30)

    laser_layer = LaserLayer("scan_lasers", width=600, height=400)
    args = InterpreterArgs(hype=80, allow_rainbows=True, min_hype=0, max_hype=100)

    interpreter = LaserScan(
        [laser_layer], args, num_beams=6, scan_speed=0.08, scan_range=140.0
    )

    scheme = ColorScheme(Color("green"), Color("red"), Color("blue"))

    print(f"\n🔍 {interpreter.num_beams} beams scanning:")

    # Show scanning progression
    for step in range(12):
        frame = Frame(
            {
                FrameSignal.freq_high: 0.7,  # High treble for scanning
                FrameSignal.freq_all: 0.6,
            }
        )

        interpreter.step(frame, scheme)

        beam_info = interpreter.get_beam_info()

        # Show scan position and direction
        direction_arrow = "→" if interpreter.scan_direction > 0 else "←"
        scan_position = interpreter.scan_phase

        print(f"   Step {step+1:2d}: {direction_arrow} scan pos {scan_position:+.2f}")

        # Show beam intensities
        if beam_info:
            intensities = [beam["intensity"] for beam in beam_info]
            avg_intensity = sum(intensities) / len(intensities)
            print(f"            avg beam intensity: {avg_intensity:.2f}")


def demo_complete_laser_show():
    """Demonstrate a complete laser show with multiple effects"""
    print("\n" + "🎆" * 30)
    print("   COMPLETE LASER SHOW")
    print("   'Multiple laser effects combined'")
    print("🎆" * 30)

    # Create multiple laser layers
    laser_layer = LaserLayer("main_lasers", width=800, height=600, beam_intensity=1.0)
    haze_layer = LaserHaze("atmosphere", width=800, height=600, haze_density=0.3)

    layers = [haze_layer, laser_layer]
    args = InterpreterArgs(hype=85, allow_rainbows=True, min_hype=0, max_hype=100)

    # Create multiple laser interpreters
    interpreters = [
        ConcertLasers([laser_layer], args, num_lasers=8, fan_angle=120.0),
        LaserMatrix([laser_layer], args, grid_size=(6, 4)),
        LaserBurst([laser_layer], args, burst_threshold=0.8, max_burst_lasers=16),
    ]

    # Simulate a complete song progression
    song_progression = [
        (
            "🎵 Intro",
            {
                FrameSignal.freq_low: 0.2,
                FrameSignal.freq_high: 0.1,
                FrameSignal.freq_all: 0.15,
                FrameSignal.sustained_low: 0.3,
            },
            "Minimal lasers, building atmosphere",
        ),
        (
            "🎶 Verse",
            {
                FrameSignal.freq_low: 0.4,
                FrameSignal.freq_high: 0.3,
                FrameSignal.freq_all: 0.35,
                FrameSignal.sustained_low: 0.5,
            },
            "Steady laser patterns",
        ),
        (
            "🔥 Build-up",
            {
                FrameSignal.freq_low: 0.7,
                FrameSignal.freq_high: 0.6,
                FrameSignal.freq_all: 0.65,
                FrameSignal.sustained_low: 0.8,
            },
            "Intensifying laser movement",
        ),
        (
            "💥 DROP!",
            {
                FrameSignal.freq_low: 0.95,
                FrameSignal.freq_high: 0.9,
                FrameSignal.freq_all: 0.92,
                FrameSignal.sustained_low: 0.9,
                FrameSignal.strobe: 1.0,
            },
            "MAXIMUM LASER INTENSITY!",
        ),
        (
            "🎭 Breakdown",
            {
                FrameSignal.freq_low: 0.3,
                FrameSignal.freq_high: 0.8,
                FrameSignal.freq_all: 0.55,
                FrameSignal.pulse: 1.0,
            },
            "Scanning and chasing effects",
        ),
        (
            "🌟 Finale",
            {
                FrameSignal.freq_low: 0.98,
                FrameSignal.freq_high: 0.96,
                FrameSignal.freq_all: 0.97,
                FrameSignal.sustained_low: 0.95,
                FrameSignal.strobe: 1.0,
                FrameSignal.pulse: 1.0,
            },
            "ALL LASER EFFECTS ACTIVE!",
        ),
    ]

    # Color schemes for different song sections
    color_schemes = [
        ColorScheme(Color("blue"), Color("white"), Color("cyan")),  # Cool intro
        ColorScheme(Color("green"), Color("yellow"), Color("lime")),  # Energetic verse
        ColorScheme(Color("orange"), Color("red"), Color("yellow")),  # Hot build-up
        ColorScheme(Color("red"), Color("white"), Color("pink")),  # Intense drop
        ColorScheme(
            Color("purple"), Color("blue"), Color("magenta")
        ),  # Mysterious breakdown
        ColorScheme(Color("white"), Color("red"), Color("gold")),  # Epic finale
    ]

    print(f"\n🎆 Laser show progression ({len(song_progression)} sections):")

    for i, (section_name, signals, description) in enumerate(song_progression):
        frame = Frame(signals)
        scheme = color_schemes[i % len(color_schemes)]

        print(f"\n{section_name}: {description}")

        # Update all laser interpreters
        active_effects = []
        for interp in interpreters:
            old_str = str(interp)
            interp.step(frame, scheme)
            new_str = str(interp)

            # Track active effects
            if old_str != new_str or any(
                keyword in new_str.lower() for keyword in ["bursting", "active"]
            ):
                active_effects.append(new_str)

        # Render the combined laser show
        haze_result = haze_layer.render(frame, scheme)
        laser_result = laser_layer.render(frame, scheme)

        # Analyze laser show intensity
        total_pixels = 0
        if haze_result is not None:
            total_pixels += np.count_nonzero(haze_result)
        if laser_result is not None:
            total_pixels += np.count_nonzero(laser_result)

        # Get laser statistics
        laser_stats = laser_layer.get_laser_stats()
        total_effects = sum(laser_stats.values())

        print(f"   🔦 Effects: {total_effects} total laser elements")
        print(f"   📊 Stats: {laser_stats}")
        print(f"   💡 Pixels: {total_pixels} illuminated")

        if active_effects:
            print(f"   ⚡ Active: {', '.join(active_effects)}")

        # Special moments
        if signals.get(FrameSignal.strobe, 0) > 0.5:
            print("   🌟 STROBE ACTIVATED - Maximum visual impact!")
        if signals.get(FrameSignal.freq_all, 0) > 0.9:
            print("   🔥 PEAK ENERGY - All laser systems firing!")


def demo_laser_color_response():
    """Demonstrate laser color response to color schemes"""
    print("\n" + "🌈" * 30)
    print("   LASER COLOR SCHEME RESPONSE")
    print("🌈" * 30)

    laser_layer = LaserLayer("color_lasers", width=400, height=300)
    args = InterpreterArgs(hype=75, allow_rainbows=True, min_hype=0, max_hype=100)

    interpreter = ConcertLasers([laser_layer], args, num_lasers=6)

    # Test different color schemes
    test_schemes = [
        ("🔴 Red Theme", ColorScheme(Color("red"), Color("darkred"), Color("pink"))),
        ("🔵 Blue Theme", ColorScheme(Color("blue"), Color("navy"), Color("cyan"))),
        (
            "🟢 Green Theme",
            ColorScheme(Color("green"), Color("darkgreen"), Color("lime")),
        ),
        ("🎃 Halloween", ColorScheme(Color("orange"), Color("black"), Color("red"))),
        ("👻 Ghostly", ColorScheme(Color("white"), Color("gray"), Color("silver"))),
        ("🌈 Rainbow", ColorScheme(Color("red"), Color("green"), Color("blue"))),
    ]

    frame = Frame(
        {
            FrameSignal.freq_low: 0.7,
            FrameSignal.freq_high: 0.6,
            FrameSignal.freq_all: 0.65,
            FrameSignal.sustained_low: 0.8,
        }
    )

    for scheme_name, scheme in test_schemes:
        print(f"\n{scheme_name}:")

        interpreter.step(frame, scheme)

        laser_info = interpreter.get_laser_info()

        if laser_info:
            # Analyze laser colors
            colors = [laser["color"] for laser in laser_info]

            print(f"   🔦 {len(laser_info)} active lasers")
            print(f"   🎨 Colors in use:")

            for j, color in enumerate(colors[:4]):  # Show first 4 colors
                r, g, b = [int(c * 255) for c in color]
                dominant = (
                    "🔴" if r > g and r > b else "🟢" if g > r and g > b else "🔵"
                )
                print(f"      Laser {j+1}: RGB({r}, {g}, {b}) {dominant}")

            if len(colors) > 4:
                print(f"      ... and {len(colors) - 4} more lasers")


def main():
    """Run the complete laser show demo"""
    try:
        demo_concert_laser_fan()
        demo_laser_matrix_patterns()
        demo_laser_chase_effects()
        demo_laser_burst_explosion()
        demo_laser_spiral_patterns()
        demo_laser_scanning()
        demo_laser_color_response()

        print("\n" + "🎆" * 40)
        print("  CONCERT LASER SYSTEM COMPLETE!")
        print("🎆" * 40)

        print("\n✨ Laser effects demonstrated:")
        print("   🔴 Concert fan lasers - beams fan out from origin point")
        print("   🔳 Matrix patterns - grid of pulsing laser points")
        print("   🏃 Chase effects - lasers chase around with trails")
        print("   💥 Burst explosions - explosive radial laser bursts")
        print("   🌀 Spiral patterns - rotating spiral laser trails")
        print("   🔍 Scanning beams - sweeping laser scan effects")
        print("   🌫️ Atmospheric haze - makes lasers more visible")

        print("\n🎵 Audio responsiveness:")
        print("   🔊 Bass - controls laser intensity and movement speed")
        print("   🎼 Treble - triggers scanning and spiral effects")
        print("   ⚡ Energy spikes - trigger explosive laser bursts")
        print("   🥁 Beat detection - drives chase and scan timing")
        print("   🎛️ Manual controls - strobe button activates all lasers")

        print("\n🎬 Perfect for concerts and parties!")
        print("   Lasers use your color scheme automatically")
        print("   Multiple laser types can run simultaneously")
        print("   All effects respond to music in real-time")

        print("\n🔴 Your Dead Sexy party will have AMAZING laser shows! 🔴")

    except Exception as e:
        print(f"Demo failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
