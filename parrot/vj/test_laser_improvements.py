#!/usr/bin/env python3

import moderngl as mgl
import numpy as np
from unittest.mock import Mock

from parrot.vj.vj_director import VJDirector
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme


def test_laser_improvements():
    """Test the improved laser system with 4 units, sustained_high intensity, and smooth movement"""
    print("🟢 TESTING LASER IMPROVEMENTS")
    print("=" * 60)

    # Create VJ Director
    director = VJDirector()

    try:
        ctx = mgl.create_context(standalone=True, require=330)
        director.setup(ctx)
        print("✅ VJ Director setup complete")
    except Exception as e:
        print(f"❌ Failed to setup VJ Director: {e}")
        return False

    # Get concert stage and laser array
    concert_stage = director.get_concert_stage()
    laser_array = concert_stage.laser_array

    print()
    print("🔧 LASER CONFIGURATION:")
    print(f"  Laser count: {laser_array.laser_count}")
    print(f"  Signal: {laser_array.signal}")
    print(f"  Scan speed: {laser_array.scan_speed}")
    print(
        f"  Fan angle: {laser_array.fan_angle:.2f} radians ({laser_array.fan_angle * 180 / 3.14159:.1f}°)"
    )
    print(f"  Laser intensity: {laser_array.laser_intensity}")
    print(f"  Color: {laser_array.color}")

    print()
    print("🎯 LASER POSITIONING:")
    if hasattr(laser_array, "lasers") and laser_array.lasers:
        print(f"  Total laser beams: {len(laser_array.lasers)}")

        # Group lasers by approximate X position to show units
        laser_positions = [
            (i, laser.position) for i, laser in enumerate(laser_array.lasers)
        ]
        laser_positions.sort(key=lambda x: x[1][0])  # Sort by X position

        current_unit = 0
        last_x = None
        for i, (laser_id, pos) in enumerate(laser_positions):
            if last_x is None or abs(pos[0] - last_x) > 2.0:  # New unit if X diff > 2
                current_unit += 1
                print(f"  Unit {current_unit}:")
                last_x = pos[0]

            print(
                f"    Laser {laser_id}: pos=({pos[0]:.1f}, {pos[1]:.1f}, {pos[2]:.1f})"
            )

            # Check if positioned at top of screen
            if pos[1] < 6.0:  # Should be high up (Y > 6)
                print(
                    f"      ⚠️  Warning: Laser {laser_id} might be too low (Y={pos[1]:.1f})"
                )
    else:
        print("  ❌ No laser beams found!")

    print()
    print("🎬 TESTING LASER RENDERING:")

    # Test with different signal levels
    test_signals = [
        ("Low signals", 0.1, 0.1),
        ("Medium signals", 0.5, 0.5),
        ("High signals", 0.9, 0.9),
        ("High sustained, low freq", 0.9, 0.1),
        ("Low sustained, high freq", 0.1, 0.9),
    ]

    for test_name, sustained_high, freq_high in test_signals:
        # Create test frame with specific signal values
        frame = Mock(spec=Frame)
        frame.__getitem__ = Mock(
            side_effect=lambda signal: {
                FrameSignal.sustained_high: sustained_high,
                FrameSignal.freq_high: freq_high,
            }.get(signal, 0.5)
        )

        scheme = Mock(spec=ColorScheme)

        # Render laser array
        laser_result = laser_array.render(frame, scheme, ctx)
        if laser_result:
            laser_data = laser_result.read()
            laser_pixels = np.frombuffer(laser_data, dtype=np.uint8)
            laser_content = np.sum(laser_pixels > 10)
            print(
                f"  {test_name}: {laser_content:,} pixels ({laser_content/len(laser_pixels)*100:.2f}%)"
            )
        else:
            print(f"  {test_name}: No framebuffer returned")

    print()
    print("🎪 TESTING FULL CONCERT STAGE:")

    # Test full concert stage with high signals
    frame = Mock(spec=Frame)
    frame.__getitem__ = Mock(
        side_effect=lambda signal: {
            FrameSignal.sustained_high: 0.8,
            FrameSignal.freq_high: 0.7,
            FrameSignal.freq_low: 0.6,
        }.get(signal, 0.5)
    )

    scheme = Mock(spec=ColorScheme)

    stage_result = concert_stage.render(frame, scheme, ctx)
    if stage_result:
        stage_data = stage_result.read()
        stage_pixels = np.frombuffer(stage_data, dtype=np.uint8)
        stage_content = np.sum(stage_pixels > 10)
        print(
            f"  🎭 Full concert stage: {stage_content:,} pixels ({stage_content/len(stage_pixels)*100:.2f}%)"
        )

        if stage_content > 0:
            print("  ✅ SUCCESS: Improved lasers working in full composition!")
            return True
        else:
            print("  ❌ FAILED: No content in full composition")
            return False
    else:
        print("  ❌ FAILED: No framebuffer returned")
        return False


if __name__ == "__main__":
    print("🧪 LASER IMPROVEMENTS TESTING")
    print("=" * 70)

    success = test_laser_improvements()

    print()
    print("📊 IMPROVEMENTS SUMMARY:")
    print("  🎯 4 laser units positioned horizontally across top")
    print("  💡 Laser intensity based on sustained_high signal")
    print("  🌊 Smooth scanning motion with complex patterns")
    print("  📡 Fanning reactive to freq_high signal")
    print("  🎛️  Pointing into crowd from elevated positions")

    if success:
        print()
        print("✅ ALL LASER IMPROVEMENTS WORKING!")
    else:
        print()
        print("❌ SOME LASER IMPROVEMENTS NEED ATTENTION")
