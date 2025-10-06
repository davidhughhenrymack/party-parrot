#!/usr/bin/env python3

import os
import numpy as np
import moderngl as mgl
import pytest
from PIL import Image

from parrot.vj.nodes.vintage_film_mask import VintageFilmMask
from parrot.vj.nodes.static_color import StaticColor
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.utils.colour import Color


class TestVintageFilmMaskGL:
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

    def test_vintage_film_mask_renders_and_saves_png(
        self, gl_context, color_scheme, tmp_path
    ):
        """Test rendering the vintage film mask with sprocket holes to PNG"""

        # Create a white background as input
        input_node = StaticColor(color=(1.0, 1.0, 1.0), width=1920, height=1080)
        input_node.enter(gl_context)

        # Create the vintage film mask
        mask_node = VintageFilmMask(
            input_node=input_node,
            width=0.7,
            height=0.6,
            corner_radius=0.08,
            center_x=0.5,
            center_y=0.5,
            edge_decay_width=0.03,
            decay_intensity=0.8,
            mask_width=1920,
            mask_height=1080,
        )

        mask_node.enter(gl_context)

        # Create frame
        frame = Frame(
            {
                FrameSignal.freq_all: 0.5,
                FrameSignal.freq_high: 0.5,
                FrameSignal.freq_low: 0.5,
                FrameSignal.sustained_high: 0.5,
                FrameSignal.sustained_low: 0.5,
            }
        )

        # Render the mask
        fb = mask_node.render(frame, color_scheme, gl_context)
        assert fb is not None

        # Read pixels
        data = fb.read(components=3)
        width, height = fb.width, fb.height

        # Convert to numpy array
        arr_uint8 = np.frombuffer(data, dtype=np.uint8).reshape((height, width, 3))

        # Flip vertically (OpenGL convention)
        arr_uint8 = np.flipud(arr_uint8)

        # Save PNG for inspection
        out_path = tmp_path / "rounded_rect_mask.png"
        img = Image.fromarray(arr_uint8, mode="RGB")
        img.save(out_path)

        # Also save to project test_output for convenience
        project_out_dir = os.path.join(os.getcwd(), "test_output")
        os.makedirs(project_out_dir, exist_ok=True)
        img.save(os.path.join(project_out_dir, "rounded_rect_mask_with_sprockets.png"))

        print(
            f"Saved mask visualization to: {project_out_dir}/rounded_rect_mask_with_sprockets.png"
        )

        # Clean up
        mask_node.exit()
        input_node.exit()
