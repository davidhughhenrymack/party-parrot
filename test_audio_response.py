#!/usr/bin/env python3
"""
Test audio responsiveness in VJ system
"""
import os
import time
import numpy as np

os.environ["TK_SILENCE_DEPRECATION"] = "1"


def test_audio_responsiveness():
    """Test if VJ effects respond to audio changes"""
    print("🎵 Testing audio responsiveness...")

    try:
        from parrot.state import State
        from parrot.director.vj_director import VJDirector
        from parrot.director.frame import Frame, FrameSignal
        from parrot.director.color_scheme import ColorScheme
        from parrot.director.mode import Mode
        from parrot.utils.colour import Color

        # Create VJ system
        state = State()
        state.set_mode(Mode.rave)

        # Suppress verbose output
        import sys
        from io import StringIO

        old_stdout = sys.stdout
        sys.stdout = StringIO()

        try:
            vj_director = VJDirector(state, width=400, height=300)
        finally:
            sys.stdout = old_stdout

        print("✅ VJ system created")

        # Test different audio scenarios
        audio_scenarios = [
            (
                "Silent",
                {
                    FrameSignal.freq_low: 0.0,
                    FrameSignal.freq_high: 0.0,
                    FrameSignal.freq_all: 0.0,
                    FrameSignal.sustained_low: 0.0,
                },
            ),
            (
                "Bass Heavy",
                {
                    FrameSignal.freq_low: 0.9,
                    FrameSignal.freq_high: 0.2,
                    FrameSignal.freq_all: 0.6,
                    FrameSignal.sustained_low: 0.8,
                },
            ),
            (
                "Treble Peak",
                {
                    FrameSignal.freq_low: 0.2,
                    FrameSignal.freq_high: 0.95,
                    FrameSignal.freq_all: 0.7,
                    FrameSignal.sustained_low: 0.3,
                },
            ),
            (
                "Full Energy",
                {
                    FrameSignal.freq_low: 0.9,
                    FrameSignal.freq_high: 0.9,
                    FrameSignal.freq_all: 0.95,
                    FrameSignal.sustained_low: 0.8,
                },
            ),
        ]

        scheme = ColorScheme(Color("red"), Color("gold"), Color("cyan"))

        for scenario_name, audio_values in audio_scenarios:
            print(f"\n🎵 Testing {scenario_name}:")

            frame = Frame(audio_values)

            # Step VJ system
            result = vj_director.step(frame, scheme)

            if result is not None:
                # Analyze visual response
                coverage = (np.count_nonzero(result) / result.size) * 100
                brightness = np.mean(result[:, :, :3])

                print(f"   Coverage: {coverage:.1f}%")
                print(f"   Brightness: {brightness:.1f}")

                # Check video layer alpha
                video_layers = [
                    l
                    for l in vj_director.vj_renderer.layers
                    if hasattr(l, "video_files")
                ]
                if video_layers:
                    video_alpha = video_layers[0].get_alpha()
                    print(f"   Video alpha: {video_alpha:.2f}")

                    if video_alpha < 0.5:
                        print(f"   ⚠️ Video alpha too low - may not be visible")
                    else:
                        print(f"   ✅ Video alpha good for visibility")

                # Check for audio responsiveness
                if scenario_name == "Silent" and brightness > 50:
                    print(f"   ⚠️ Too bright for silent audio")
                elif scenario_name == "Full Energy" and brightness < 20:
                    print(f"   ⚠️ Too dark for full energy")
                else:
                    print(f"   ✅ Appropriate response to audio")
            else:
                print(f"   ❌ No render output")

        vj_director.cleanup()
        return True

    except Exception as e:
        print(f"❌ Audio response test failed: {e}")
        import traceback

        traceback.print_exc()
        return False


def main():
    """Test audio responsiveness"""
    print("🎵" * 40)
    print("  AUDIO RESPONSE TEST")
    print("🎵" * 40)

    success = test_audio_responsiveness()

    if success:
        print("\n✅ Audio response test completed")
        print("🎵 VJ effects should respond to audio changes")
    else:
        print("\n❌ Audio response test failed")


if __name__ == "__main__":
    main()
