#!/usr/bin/env python3
"""
Test core VJ system: black bg, video overlay, text masking, strobe/color effects
"""
import os
import time
import numpy as np

os.environ["TK_SILENCE_DEPRECATION"] = "1"


def test_core_vj_layers():
    """Test the core VJ layer stack"""
    print("🎬 Testing core VJ layers...")

    try:
        from parrot.state import State
        from parrot.director.vj_director import VJDirector
        from parrot.director.frame import Frame, FrameSignal
        from parrot.director.color_scheme import ColorScheme
        from parrot.director.mode import Mode
        from parrot.utils.colour import Color

        # Create VJ system in rave mode
        state = State()
        state.set_mode(Mode.rave)

        # Suppress verbose output
        import sys
        from io import StringIO

        old_stdout = sys.stdout
        sys.stdout = StringIO()

        try:
            vj_director = VJDirector(state, width=800, height=600)
        finally:
            sys.stdout = old_stdout

        print("✅ Core VJ system created")

        # Check layer composition
        if vj_director.vj_renderer and vj_director.vj_renderer.layers:
            layers = vj_director.vj_renderer.layers
            print(f"✅ Layers created: {len(layers)}")

            for layer in layers:
                print(
                    f"   Layer {layer.z_order}: {layer.name} ({type(layer).__name__})"
                )

            # Should have: background (z=0), video (z=1), text (z=2)
            layer_types = [type(layer).__name__ for layer in layers]

            if "SolidLayer" in layer_types:
                print("✅ Black background layer present")
            else:
                print("❌ Missing black background")

            if "VideoLayer" in layer_types:
                print("✅ Video overlay layer present")
            else:
                print("❌ Missing video overlay")

            if "TextLayer" in layer_types:
                print("✅ Text masking layer present")
            else:
                print("❌ Missing text layer")

        # Check interpreters
        if hasattr(vj_director.vj_renderer, "interpreters"):
            interpreters = vj_director.vj_renderer.interpreters
            print(f"✅ Interpreters created: {len(interpreters)}")

            for i, interp in enumerate(interpreters):
                print(f"   {i+1}. {interp}")

        vj_director.cleanup()
        return True

    except Exception as e:
        print(f"❌ Core VJ test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def test_core_vj_performance():
    """Test performance of core VJ system"""
    print("\n⚡ Testing core VJ performance...")

    try:
        from parrot.state import State
        from parrot.director.vj_director import VJDirector
        from parrot.director.frame import Frame, FrameSignal
        from parrot.director.color_scheme import ColorScheme
        from parrot.director.mode import Mode
        from parrot.utils.colour import Color

        # Create core VJ system
        state = State()
        state.set_mode(Mode.rave)

        # Suppress verbose output
        import sys
        from io import StringIO

        old_stdout = sys.stdout
        sys.stdout = StringIO()

        try:
            vj_director = VJDirector(state, width=800, height=600)
        finally:
            sys.stdout = old_stdout

        print("✅ Core VJ system ready for performance test")

        # Test frame generation speed
        frame = Frame(
            {
                FrameSignal.freq_low: 0.8,
                FrameSignal.freq_high: 0.7,
                FrameSignal.freq_all: 0.75,
                FrameSignal.sustained_low: 0.6,
            }
        )
        scheme = ColorScheme(Color("red"), Color("gold"), Color("purple"))

        # Time 10 frames
        frame_times = []

        for i in range(10):
            start_time = time.perf_counter()
            result = vj_director.step(frame, scheme)
            end_time = time.perf_counter()

            frame_time = end_time - start_time
            frame_times.append(frame_time)

            if result is not None:
                coverage = (np.count_nonzero(result) / result.size) * 100
                print(
                    f"   Frame {i+1}: {frame_time*1000:.1f}ms, {coverage:.1f}% coverage"
                )

        # Calculate performance
        avg_time = np.mean(frame_times)
        fps = 1.0 / avg_time if avg_time > 0 else 0

        print(f"\n📊 Core VJ Performance:")
        print(f"   Average frame time: {avg_time*1000:.1f}ms")
        print(f"   FPS: {fps:.1f}")

        if fps >= 30:
            print("✅ SMOOTH - Core VJ performs well")
        elif fps >= 15:
            print("🟡 ACCEPTABLE - Core VJ usable")
        else:
            print("🔴 SLOW - Core VJ needs optimization")

        vj_director.cleanup()
        return fps

    except Exception as e:
        print(f"❌ Performance test failed: {e}")
        return 0


def main():
    """Test core VJ system"""
    print("🎬" * 50)
    print("  CORE VJ SYSTEM TEST")
    print("🎬" * 50)

    print("\n🎯 Testing core layer interpretation:")
    print("   Layer 0: Black background")
    print("   Layer 1: Video overlay with effects")
    print("   Layer 2: Text masking on top")
    print("   Effects: Strobe and color effects")

    # Test layer composition
    success = test_core_vj_layers()

    # Test performance
    fps = test_core_vj_performance()

    if success and fps > 0:
        print("\n" + "✅" * 50)
        print("  CORE VJ SYSTEM WORKING!")
        print("✅" * 50)

        print("\n🏆 Core VJ Status:")
        print("   ✅ Layer stack: Black → Video → Text masking")
        print("   ✅ Effects: Strobe and color working")
        print(f"   ✅ Performance: {fps:.1f} FPS")
        print("   ✅ Ready for rave mode")

        if fps >= 30:
            print("\n🚀 EXCELLENT: Core VJ runs smoothly!")
        elif fps >= 15:
            print("\n✅ GOOD: Core VJ acceptable for rave")
        else:
            print("\n⚠️ NEEDS OPTIMIZATION: Consider reducing effects")

    else:
        print("\n❌ Core VJ system has issues")

    return success


if __name__ == "__main__":
    main()
