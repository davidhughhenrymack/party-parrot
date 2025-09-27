#!/usr/bin/env python3

import os
import argparse
import numpy as np
import moderngl as mgl
from PIL import Image

from parrot.vj.nodes.laser_array import LaserArray
from parrot.director.color_scheme import ColorScheme
from parrot.director.frame import Frame, FrameSignal
from parrot.utils.colour import Color


def main():
    parser = argparse.ArgumentParser(description="Render LaserArray to PNG")
    parser.add_argument(
        "--out", default="test_output/laser_array.png", help="Output PNG path"
    )
    parser.add_argument("--width", type=int, default=1280)
    parser.add_argument("--height", type=int, default=720)
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.out), exist_ok=True)

    try:
        ctx = mgl.create_context(standalone=True, backend="egl")
    except Exception:
        ctx = mgl.create_context(standalone=True)

    # Camera setup matches ConcertStage
    camera_eye = np.array([0.0, 6.0, -8.0], dtype=np.float32)
    camera_target = np.array([0.0, 6.0, 0.0], dtype=np.float32)
    camera_up = np.array([0.0, 1.0, 0.0], dtype=np.float32)

    # Laser positioned top-left of stage, pointing toward audience
    laser_position = np.array([-4.0, 8.0, 2.0], dtype=np.float32)
    laser_point_vector = camera_eye - laser_position
    laser_point_vector = laser_point_vector / np.linalg.norm(laser_point_vector)

    node = LaserArray(
        camera_eye=camera_eye,
        camera_target=camera_target,
        camera_up=camera_up,
        laser_position=laser_position,
        laser_point_vector=laser_point_vector,
        laser_count=1,
        laser_length=40.0,
        laser_thickness=10.0,
        width=args.width,
        height=args.height,
    )
    node.enter(ctx)

    frame = Frame(
        {
            FrameSignal.freq_all: 0.8,
            FrameSignal.freq_high: 0.8,
            FrameSignal.freq_low: 0.8,
            FrameSignal.sustained_high: 0.8,
            FrameSignal.sustained_low: 0.8,
        }
    )
    scheme = ColorScheme(
        fg=Color("white"), bg=Color("black"), bg_contrast=Color("white")
    )

    fb = node.render(frame, scheme, ctx)
    if fb is None:
        raise RuntimeError("LaserArray returned no framebuffer")

    data = fb.read(components=4, dtype="u1")
    img = Image.frombytes("RGBA", (fb.width, fb.height), data)
    img = img.transpose(Image.FLIP_TOP_BOTTOM)  # match typical GL orientation
    img.save(args.out)
    print(f"Saved {args.out}")


if __name__ == "__main__":
    main()
