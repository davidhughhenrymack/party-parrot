#!/usr/bin/env python3

import os
import numpy as np
import moderngl as mgl
import pytest
from PIL import Image

from parrot.vj.nodes.bright_glow import BrightGlow
from parrot.vj.nodes.static_color import StaticColor
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.utils.colour import Color


class TestBrightGlowGL:
    @pytest.fixture
    def gl_context(self):
        try:
            ctx = mgl.create_context(standalone=True, backend="egl")
            yield ctx
        except Exception:
            ctx = mgl.create_context(standalone=True)
            yield ctx

    @pytest.fixture
    def color_scheme(self):
        return ColorScheme(
            fg=Color("white"), bg=Color("black"), bg_contrast=Color("white")
        )

    def test_bright_glow_renders_and_saves_png(
        self, gl_context, color_scheme, tmp_path
    ):
        """Test rendering the bright glow effect to PNG"""

        # Create a test pattern with some bright areas
        # Make a gradient with bright center and darker edges
        width, height = 1920, 1080
        input_node = StaticColor(color=(1.0, 1.0, 1.0), width=width, height=height)
        input_node.enter(gl_context)

        # Create a simple pattern by rendering once to get a base
        frame = Frame(
            {
                FrameSignal.freq_all: 0.8,
                FrameSignal.freq_high: 0.9,
                FrameSignal.freq_low: 0.5,
                FrameSignal.sustained_high: 0.7,
                FrameSignal.sustained_low: 0.6,
            }
        )

        # Create the bright glow effect
        glow_node = BrightGlow(
            input_node=input_node,
            brightness_threshold=0.75,
            blur_radius=8,
            glow_intensity=0.1,
        )

        glow_node.enter(gl_context)

        # Render the glow effect
        fb = glow_node.render(frame, color_scheme, gl_context)
        assert fb is not None

        # Read pixels
        data = fb.read(components=3)
        width, height = fb.width, fb.height

        # Convert to numpy array
        arr_uint8 = np.frombuffer(data, dtype=np.uint8).reshape((height, width, 3))

        # Flip vertically (OpenGL convention)
        arr_uint8 = np.flipud(arr_uint8)

        # Save PNG for inspection
        out_path = tmp_path / "bright_glow.png"
        img = Image.fromarray(arr_uint8, mode="RGB")
        img.save(out_path)

        # Also save to project test_output for convenience
        project_out_dir = os.path.join(os.getcwd(), "test_output")
        os.makedirs(project_out_dir, exist_ok=True)
        img.save(os.path.join(project_out_dir, "bright_glow_effect.png"))

        print(
            f"\n✅ Saved glow visualization to: {project_out_dir}/bright_glow_effect.png"
        )
        print(f"   - Brightness threshold: 75%")
        print(f"   - Blur radius: 8 passes")
        print(f"   - Glow intensity: 10%")

        # Clean up
        glow_node.exit()
        input_node.exit()

    def test_bright_glow_with_gradient_pattern(
        self, gl_context, color_scheme, tmp_path
    ):
        """Test bright glow with a more interesting pattern"""

        # Create a test pattern with bright spots
        # We'll create a simple white input and let the effect show what it does
        width, height = 1920, 1080
        input_node = StaticColor(color=(0.9, 0.9, 0.9), width=width, height=height)
        input_node.enter(gl_context)

        frame = Frame(
            {
                FrameSignal.freq_all: 1.0,
                FrameSignal.freq_high: 1.0,
                FrameSignal.freq_low: 0.3,
                FrameSignal.sustained_high: 0.9,
                FrameSignal.sustained_low: 0.4,
            }
        )

        # Create glow with higher intensity to see the effect clearly
        glow_node = BrightGlow(
            input_node=input_node,
            brightness_threshold=0.6,  # Lower threshold to see more glow
            blur_radius=12,  # More blur for dramatic effect
            glow_intensity=0.3,  # Higher intensity for visibility
        )

        glow_node.enter(gl_context)

        # Render
        fb = glow_node.render(frame, color_scheme, gl_context)
        assert fb is not None

        # Read and save
        data = fb.read(components=3)
        width, height = fb.width, fb.height
        arr_uint8 = np.frombuffer(data, dtype=np.uint8).reshape((height, width, 3))
        arr_uint8 = np.flipud(arr_uint8)

        # Save to project output
        project_out_dir = os.path.join(os.getcwd(), "test_output")
        os.makedirs(project_out_dir, exist_ok=True)
        img = Image.fromarray(arr_uint8, mode="RGB")
        img.save(os.path.join(project_out_dir, "bright_glow_dramatic.png"))

        print(
            f"\n✅ Saved dramatic glow to: {project_out_dir}/bright_glow_dramatic.png"
        )

        # Clean up
        glow_node.exit()
        input_node.exit()
