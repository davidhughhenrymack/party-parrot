#!/usr/bin/env python3

import os
import numpy as np
import moderngl as mgl
import pytest
from PIL import Image

from parrot.vj.nodes.laser_array import LaserArray
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.utils.colour import Color


class TestLaserArrayGL:
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

    def test_laser_array_renders_and_saves_png(
        self, gl_context, color_scheme, tmp_path
    ):
        # Camera setup matches ConcertStage
        camera_eye = np.array([0.0, 6.0, -8.0], dtype=np.float32)
        camera_target = np.array([0.0, 6.0, 0.0], dtype=np.float32)
        camera_up = np.array([0.0, 1.0, 0.0], dtype=np.float32)

        # Place a beam clearly inside the camera frustum for test reliability
        laser_position = np.array(
            [0.0, 6.0, -3.0], dtype=np.float32
        )  # in front of camera, centered
        laser_point_vector = np.array(
            [0.0, 0.0, 1.0], dtype=np.float32
        )  # forward into the scene

        node = LaserArray(
            camera_eye=camera_eye,
            camera_target=camera_target,
            camera_up=camera_up,
            laser_position=laser_position,
            laser_point_vector=laser_point_vector,
            laser_count=1,
            laser_length=5.0,
            laser_thickness=1.0,
        )

        node.enter(gl_context)

        # Real Frame with high signals
        frame = Frame(
            {
                FrameSignal.freq_all: 0.9,
                FrameSignal.freq_high: 0.9,
                FrameSignal.freq_low: 0.9,
                FrameSignal.sustained_high: 0.9,
                FrameSignal.sustained_low: 0.9,
            }
        )

        fb = node.render(frame, color_scheme, gl_context)
        assert fb is not None

        # Read pixels and check for non-black content
        data = fb.read(components=4, dtype="u1")
        width, height = fb.width, fb.height
        arr = np.frombuffer(data, dtype=np.uint8).reshape((height, width, 4))
        rgb = arr[:, :, :3]
        non_black = np.sum(rgb > 8)
        assert non_black > 0

        # Save PNG for inspection
        out_path = tmp_path / "laser_array.png"
        img = Image.fromarray(arr, mode="RGBA")
        img.save(out_path)

        # Also save to project test_output for convenience
        project_out_dir = os.path.join(os.getcwd(), "test_output")
        os.makedirs(project_out_dir, exist_ok=True)
        img.save(os.path.join(project_out_dir, "laser_array.png"))
