#!/usr/bin/env python3

import moderngl as mgl
import numpy as np
from unittest.mock import Mock

from parrot.vj.nodes.layer_compose import LayerCompose, LayerSpec, BlendMode
from parrot.vj.nodes.black import Black
from parrot.vj.nodes.volumetric_beam import VolumetricBeam
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme


def test_black_plus_beam_composition():
    """Test that Black + VolumetricBeam composition has non-black pixels"""
    print("🔍 TESTING BLACK + VOLUMETRIC BEAM COMPOSITION")
    print("=" * 60)

    # Create components
    black = Black()
    beam = VolumetricBeam(
        beam_count=3,
        beam_length=10.0,
        beam_width=0.5,
        beam_intensity=3.0,  # High intensity
        haze_density=1.0,  # Maximum haze
        movement_speed=1.0,
        color=(1.0, 0.8, 0.6),
        signal=FrameSignal.freq_low,
    )

    # Create layer composition
    layer_compose = LayerCompose(
        LayerSpec(black, BlendMode.NORMAL),
        LayerSpec(beam, BlendMode.NORMAL),
    )

    # Setup GL context
    try:
        ctx = mgl.create_context(standalone=True, require=330)
        print("✅ OpenGL context created")
    except Exception as e:
        print(f"❌ Failed to create OpenGL context: {e}")
        return False

    # Setup components
    layer_compose.enter_recursive(ctx)
    print("✅ Components setup complete")

    # Create test frame
    frame = Mock(spec=Frame)
    frame.__getitem__ = Mock(return_value=0.8)  # High signal
    scheme = Mock(spec=ColorScheme)

    print()
    print("🎬 TESTING INDIVIDUAL COMPONENTS:")

    # Test black layer
    black_result = black.render(frame, scheme, ctx)
    if black_result:
        black_data = black_result.read()
        black_pixels = np.frombuffer(black_data, dtype=np.uint8)
        black_content = np.sum(black_pixels > 10)
        print(
            f"  📦 Black: {black_content:,} pixels ({black_content/len(black_pixels)*100:.3f}%)"
        )

    # Test beam layer
    beam_result = beam.render(frame, scheme, ctx)
    if beam_result:
        beam_data = beam_result.read()
        beam_pixels = np.frombuffer(beam_data, dtype=np.uint8)
        beam_content = np.sum(beam_pixels > 10)
        print(
            f"  🌫️  Beam: {beam_content:,} pixels ({beam_content/len(beam_pixels)*100:.3f}%)"
        )

        if beam_content == 0:
            print("  🚨 PROBLEM: Beam has no visible content!")

            # Debug beam parameters
            print(f"    - Beam count: {beam.beam_count}")
            print(f"    - Beam intensity: {beam.beam_intensity}")
            print(f"    - Haze density: {beam.haze_density}")
            print(f"    - Context: {beam._context is not None}")
            print(f"    - Framebuffer: {beam.framebuffer is not None}")
            print(f"    - Program: {beam.beam_program is not None}")

    print()
    print("🎪 TESTING COMPOSITION:")

    # Test composition
    compose_result = layer_compose.render(frame, scheme, ctx)
    if compose_result:
        compose_data = compose_result.read()
        compose_pixels = np.frombuffer(compose_data, dtype=np.uint8)
        compose_content = np.sum(compose_pixels > 10)
        print(
            f"  🎭 Composition: {compose_content:,} pixels ({compose_content/len(compose_pixels)*100:.3f}%)"
        )

        if compose_content > 0:
            print("  ✅ SUCCESS: Composition has visible content!")
            return True
        else:
            print("  ❌ FAILED: Composition has no visible content!")
            return False
    else:
        print("  ❌ FAILED: No composition result")
        return False


def test_concert_stage_beam_visibility():
    """Test that ConcertStage volumetric beams are visible"""
    print()
    print("🎪 TESTING CONCERT STAGE BEAM VISIBILITY")
    print("=" * 60)

    from parrot.vj.vj_director import VJDirector

    # Create VJ Director
    director = VJDirector()

    try:
        ctx = mgl.create_context(standalone=True, require=330)
        director.setup(ctx)
        print("✅ VJ Director setup complete")
    except Exception as e:
        print(f"❌ Failed to setup VJ Director: {e}")
        return False

    # Get concert stage
    concert_stage = director.get_concert_stage()

    # Create test frame
    frame = Mock(spec=Frame)
    frame.__getitem__ = Mock(return_value=0.8)  # High signal
    scheme = Mock(spec=ColorScheme)

    print()
    print("🌫️  TESTING VOLUMETRIC BEAMS IN CONCERT STAGE:")

    # Test volumetric beams directly
    beam_result = concert_stage.volumetric_beams.render(frame, scheme, ctx)
    if beam_result:
        beam_data = beam_result.read()
        beam_pixels = np.frombuffer(beam_data, dtype=np.uint8)
        beam_content = np.sum(beam_pixels > 10)
        print(
            f"  🌫️  Direct beam render: {beam_content:,} pixels ({beam_content/len(beam_pixels)*100:.3f}%)"
        )

        if beam_content == 0:
            print("  🚨 PROBLEM: Concert stage beams have no visible content!")

            # Debug beam parameters
            beam = concert_stage.volumetric_beams
            print(f"    - Beam count: {beam.beam_count}")
            print(f"    - Beam intensity: {beam.beam_intensity}")
            print(f"    - Haze density: {beam.haze_density}")
            print(f"    - Color: {beam.color}")
            print(f"    - Signal: {beam.signal}")

    # Test full concert stage
    stage_result = concert_stage.render(frame, scheme, ctx)
    if stage_result:
        stage_data = stage_result.read()
        stage_pixels = np.frombuffer(stage_data, dtype=np.uint8)
        stage_content = np.sum(stage_pixels > 10)
        print(
            f"  🎭 Full concert stage: {stage_content:,} pixels ({stage_content/len(stage_pixels)*100:.3f}%)"
        )

        return stage_content > 0

    return False


if __name__ == "__main__":
    print("🧪 BEAM VISIBILITY TESTING")
    print("=" * 70)

    # Test 1: Basic black + beam composition
    test1_success = test_black_plus_beam_composition()

    # Test 2: Concert stage beam visibility
    test2_success = test_concert_stage_beam_visibility()

    print()
    print("📊 TEST RESULTS:")
    print(f'  Test 1 (Black + Beam): {"✅ PASS" if test1_success else "❌ FAIL"}')
    print(f'  Test 2 (Concert Stage): {"✅ PASS" if test2_success else "❌ FAIL"}')

    if not test1_success or not test2_success:
        print()
        print("🔧 BEAM VISIBILITY ISSUES DETECTED!")
        print("Need to investigate beam rendering parameters.")
    else:
        print()
        print("✅ ALL BEAM VISIBILITY TESTS PASSED!")
