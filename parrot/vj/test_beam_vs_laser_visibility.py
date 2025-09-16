#!/usr/bin/env python3

import moderngl as mgl
import numpy as np
from unittest.mock import Mock

from parrot.vj.vj_director import VJDirector
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme


def test_beam_vs_laser_visibility():
    """Compare volumetric beam vs laser visibility in the full composition"""
    print("🔍 BEAM VS LASER VISIBILITY COMPARISON")
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

    # Get concert stage components
    concert_stage = director.get_concert_stage()

    # Create test frame with high signals
    frame = Mock(spec=Frame)
    frame.__getitem__ = Mock(
        side_effect=lambda signal: {
            FrameSignal.sustained_high: 0.9,
            FrameSignal.freq_high: 0.8,
            FrameSignal.freq_low: 0.7,
        }.get(signal, 0.6)
    )

    scheme = Mock(spec=ColorScheme)

    print()
    print("🎬 INDIVIDUAL COMPONENT ANALYSIS:")

    # Test each layer individually
    components = [
        ("Black Background", concert_stage.layer_compose.layer_specs[0].node),
        ("Canvas 2D (Video+Text)", concert_stage.layer_compose.layer_specs[1].node),
        ("Volumetric Beams", concert_stage.layer_compose.layer_specs[2].node),
        ("Laser Array", concert_stage.layer_compose.layer_specs[3].node),
    ]

    component_results = {}

    for name, component in components:
        result = component.render(frame, scheme, ctx)
        if result:
            data = result.read()
            pixels = np.frombuffer(data, dtype=np.uint8)
            content = np.sum(pixels > 10)
            percentage = content / len(pixels) * 100
            component_results[name] = (content, percentage)
            print(f"  {name}: {content:,} pixels ({percentage:.2f}%)")
        else:
            component_results[name] = (0, 0.0)
            print(f"  {name}: No framebuffer returned")

    print()
    print("🎪 FULL COMPOSITION ANALYSIS:")

    # Test full composition
    stage_result = concert_stage.render(frame, scheme, ctx)
    if stage_result:
        stage_data = stage_result.read()
        stage_pixels = np.frombuffer(stage_data, dtype=np.uint8)
        stage_content = np.sum(stage_pixels > 10)
        stage_percentage = stage_content / len(stage_pixels) * 100
        print(
            f"  🎭 Full Concert Stage: {stage_content:,} pixels ({stage_percentage:.2f}%)"
        )

        # Analysis
        beam_content, beam_percentage = component_results.get(
            "Volumetric Beams", (0, 0.0)
        )
        laser_content, laser_percentage = component_results.get("Laser Array", (0, 0.0))
        canvas_content, canvas_percentage = component_results.get(
            "Canvas 2D (Video+Text)", (0, 0.0)
        )

        print()
        print("🔍 VISIBILITY ANALYSIS:")

        if beam_content > 0:
            print(f"  ✅ Volumetric Beams ARE rendering ({beam_percentage:.2f}%)")
            if beam_percentage < 1.0:
                print(
                    f"      💡 Beams are subtle - only {beam_percentage:.2f}% of pixels"
                )
                print(
                    f"      🎨 May be overwhelmed by brighter canvas content ({canvas_percentage:.2f}%)"
                )
        else:
            print(f"  ❌ Volumetric Beams NOT rendering")

        if laser_content > 0:
            print(f"  ✅ Laser Array IS rendering ({laser_percentage:.2f}%)")
            if laser_percentage > beam_percentage:
                print(
                    f"      🔥 Lasers are {laser_percentage/beam_percentage:.1f}x more visible than beams"
                )
        else:
            print(f"  ❌ Laser Array NOT rendering")

        # Check composition efficiency
        individual_total = sum(content for content, _ in component_results.values())
        if individual_total > 0:
            composition_efficiency = stage_content / individual_total * 100
            print(f"  📊 Composition efficiency: {composition_efficiency:.1f}%")

            if composition_efficiency < 80:
                print(f"      ⚠️  Some content may be lost in blending")

        print()
        print("💡 RECOMMENDATIONS:")

        if beam_percentage < 1.0:
            print("  🌫️  VOLUMETRIC BEAMS:")
            print("     - Increase beam_intensity (currently 2.5)")
            print("     - Increase haze_density (currently 0.9)")
            print("     - Consider using ADDITIVE blend mode instead of NORMAL")
            print("     - Beams may be too subtle compared to bright video content")

        if laser_percentage > 0:
            print("  🟢 LASER ARRAY:")
            print("     - Working well with ADDITIVE blending")
            print("     - Good visibility with sustained_high intensity control")
            print("     - 4-unit horizontal positioning effective")

        return True
    else:
        print("  ❌ FAILED: No framebuffer returned")
        return False


if __name__ == "__main__":
    print("🧪 BEAM VS LASER VISIBILITY TESTING")
    print("=" * 70)

    success = test_beam_vs_laser_visibility()

    if success:
        print()
        print("✅ VISIBILITY ANALYSIS COMPLETE!")
        print("📋 Check recommendations above for improving beam visibility.")
    else:
        print()
        print("❌ VISIBILITY ANALYSIS FAILED!")
