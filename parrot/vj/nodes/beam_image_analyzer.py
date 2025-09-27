#!/usr/bin/env python3

import argparse
import cv2
import numpy as np


def detect_beam_like_lines(image_path: str) -> dict:
    img = cv2.imread(image_path, cv2.IMREAD_COLOR)
    if img is None:
        raise FileNotFoundError(image_path)

    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    # Boost contrast
    gray = cv2.equalizeHist(gray)

    # Edge detection
    edges = cv2.Canny(gray, 50, 150, apertureSize=3)

    # Probabilistic Hough transform to find line segments
    lines = cv2.HoughLinesP(
        edges, 1, np.pi / 180, threshold=80, minLineLength=60, maxLineGap=10
    )

    h, w = gray.shape

    total_pixels = h * w
    bright_ratio = float(np.sum(gray > 40)) / total_pixels

    num_lines = 0 if lines is None else len(lines)

    # Heuristic: consider it "beam-like" if we have at least 2 long-ish lines and enough bright pixels
    looks_like_beams = num_lines >= 2 and bright_ratio > 0.02

    return {
        "width": w,
        "height": h,
        "bright_ratio": bright_ratio,
        "num_lines": num_lines,
        "looks_like_beams": looks_like_beams,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Analyze laser/beam PNG for beam-like lines"
    )
    parser.add_argument("image", help="Path to image to analyze")
    args = parser.parse_args()

    result = detect_beam_like_lines(args.image)
    print(result)


if __name__ == "__main__":
    main()
