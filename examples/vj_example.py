#!/usr/bin/env python3
"""
Example demonstrating the VJ system functionality
"""
import time
import numpy as np
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.director.mode import Mode
from parrot.interpreters.base import InterpreterArgs
from parrot.utils.colour import Color
from parrot.vj.renderer import ModernGLRenderer
from parrot.vj.base import SolidLayer
from parrot.vj.layers.text import TextLayer
from parrot.vj.layers.video import VideoLayer
from parrot.vj.interpreters.alpha_fade import AlphaFade
from parrot.vj.interpreters.text_animator import TextPulse
from parrot.vj.vj_interpretations import create_vj_renderer


def demo_basic_renderer():
    """Demonstrate basic VJ renderer functionality"""
    print("=== Basic VJ Renderer Demo ===")

    # Create renderer
    renderer = ModernGLRenderer(400, 300)

    # Create layers
    background = SolidLayer(
        "background", (0, 0, 0), 255, z_order=0, width=400, height=300
    )
    foreground = SolidLayer(
        "foreground", (255, 128, 64), 128, z_order=1, width=400, height=300
    )

    renderer.add_layer(background)
    renderer.add_layer(foreground)

    # Create test frame and color scheme
    frame = Frame({FrameSignal.freq_low: 0.5})
    scheme = ColorScheme(Color("red"), Color("blue"), Color("green"))

    # Render frame
    result = renderer.render_frame(frame, scheme)

    if result is not None:
        print(f"Rendered frame: {result.shape}, dtype: {result.dtype}")
        print(f"Sample pixel: {result[150, 200]}")  # Center pixel
    else:
        print("No frame rendered (GPU not available)")

    renderer.cleanup()


def demo_text_layer():
    """Demonstrate text layer with alpha masking"""
    print("\n=== Text Layer Demo ===")

    renderer = ModernGLRenderer(600, 400)

    # Background layer
    bg_layer = SolidLayer("bg", (64, 32, 128), 255, z_order=0, width=600, height=400)

    # Text layer with alpha masking
    text_layer = TextLayer(
        "PARTY", "text", alpha_mask=True, z_order=1, width=600, height=400
    )

    renderer.add_layer(bg_layer)
    renderer.add_layer(text_layer)

    frame = Frame({})
    scheme = ColorScheme(Color("white"), Color("black"), Color("gray"))

    result = renderer.render_frame(frame, scheme)

    if result is not None:
        print(f"Text layer rendered: {result.shape}")
        # Check if text masking worked (should have transparent areas)
        alpha_values = result[:, :, 3]
        print(f"Alpha range: {alpha_values.min()} - {alpha_values.max()}")
        print(f"Has transparency: {np.any(alpha_values < 255)}")

    renderer.cleanup()


def demo_interpreters():
    """Demonstrate VJ interpreters"""
    print("\n=== VJ Interpreters Demo ===")

    renderer = ModernGLRenderer(400, 300)

    # Create layers
    bg_layer = SolidLayer("bg", (0, 0, 0), 255, z_order=0, width=400, height=300)
    video_layer = SolidLayer(
        "fake_video", (255, 0, 0), 255, z_order=1, width=400, height=300
    )
    text_layer = TextLayer(
        "VJ", "text", alpha_mask=True, z_order=2, width=400, height=300
    )

    renderer.add_layer(bg_layer)
    renderer.add_layer(video_layer)
    renderer.add_layer(text_layer)

    # Create interpreters
    args = InterpreterArgs(hype=50, allow_rainbows=True, min_hype=0, max_hype=100)

    alpha_interpreter = AlphaFade(
        [video_layer], args, signal=FrameSignal.freq_low, min_alpha=0.2, max_alpha=1.0
    )

    text_interpreter = TextPulse(
        [text_layer],
        args,
        pulse_signal=FrameSignal.freq_high,
        min_scale=0.8,
        max_scale=1.5,
    )

    # Simulate different audio conditions
    test_frames = [
        Frame({FrameSignal.freq_low: 0.2, FrameSignal.freq_high: 0.1}),  # Low energy
        Frame({FrameSignal.freq_low: 0.8, FrameSignal.freq_high: 0.9}),  # High energy
        Frame({FrameSignal.freq_low: 0.5, FrameSignal.freq_high: 0.3}),  # Medium energy
    ]

    scheme = ColorScheme(Color("cyan"), Color("magenta"), Color("yellow"))

    for i, frame in enumerate(test_frames):
        print(
            f"\nFrame {i+1}: low={frame[FrameSignal.freq_low]:.1f}, "
            f"high={frame[FrameSignal.freq_high]:.1f}"
        )

        # Update interpreters
        alpha_interpreter.step(frame, scheme)
        text_interpreter.step(frame, scheme)

        # Render
        result = renderer.render_frame(frame, scheme)

        if result is not None:
            print(f"  Video layer alpha: {video_layer.get_alpha():.2f}")
            if hasattr(text_layer, "text_scale"):
                print(f"  Text scale: {text_layer.text_scale:.2f}")

    renderer.cleanup()


def demo_mode_interpretations():
    """Demonstrate mode-based VJ setup"""
    print("\n=== Mode Interpretations Demo ===")

    args = InterpreterArgs(hype=60, allow_rainbows=True, min_hype=0, max_hype=100)

    # Test different modes
    modes = [Mode.blackout, Mode.gentle, Mode.rave]

    for mode in modes:
        print(f"\nTesting mode: {mode.name}")

        try:
            renderer = create_vj_renderer(mode, args, width=320, height=240)

            print(f"  Layers: {len(renderer.layers)}")
            for layer in renderer.layers:
                print(f"    - {layer}")

            print(f"  Interpreters: {len(renderer.interpreters)}")
            for interp in renderer.interpreters:
                print(f"    - {interp}")

            # Test rendering
            frame = Frame({FrameSignal.freq_low: 0.6, FrameSignal.freq_high: 0.4})
            scheme = ColorScheme(Color("red"), Color("blue"), Color("white"))

            # Update interpreters
            for interp in renderer.interpreters:
                interp.step(frame, scheme)

            # Render
            result = renderer.render_frame(frame, scheme)

            if result is not None:
                print(
                    f"  Rendered: {result.shape}, non-zero pixels: {np.count_nonzero(result)}"
                )

            renderer.cleanup()

        except Exception as e:
            print(f"  Error: {e}")


def main():
    """Run all VJ system demos"""
    print("Party Parrot VJ System Demo")
    print("===========================")

    try:
        demo_basic_renderer()
        demo_text_layer()
        demo_interpreters()
        demo_mode_interpretations()

        print("\n=== Demo Complete ===")
        print("VJ system is working! Press SPACE in the main GUI to see it in action.")

    except Exception as e:
        print(f"Demo failed: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    main()
