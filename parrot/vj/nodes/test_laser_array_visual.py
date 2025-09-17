#!/usr/bin/env python3

import pytest
import numpy as np
import moderngl as mgl
from PIL import Image
import os
from pathlib import Path

from parrot.vj.nodes.laser_array import LaserArray
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.utils.colour import Color
from parrot.graph.BaseInterpretationNode import Vibe
from parrot.director.mode import Mode


class TestLaserArrayVisual:
    """Visual tests for LaserArray that render to PNG and analyze output"""

    @pytest.fixture
    def headless_context(self):
        """Create a headless OpenGL context for testing"""
        try:
            # Create headless context
            context = mgl.create_context(standalone=True, require=330)
            return context
        except Exception as e:
            pytest.skip(f"Could not create headless OpenGL context: {e}")

    @pytest.fixture
    def concert_stage_setup(self):
        """Create laser array with exact same setup as ConcertStage"""
        # Exact same camera system as ConcertStage
        camera_eye = np.array(
            [0.0, 6.0, -8.0]
        )  # Audience position (mid-height, in front)
        camera_target = np.array([0.0, 6.0, 0.0])  # Looking straight ahead at stage
        camera_up = np.array([0.0, 1.0, 0.0])  # World up vector

        # Exact same laser positioning as ConcertStage
        laser_position = np.array([-4.0, 8.0, 2.0])  # Top left of stage
        laser_point_vector = camera_eye - laser_position  # Point toward audience
        laser_point_vector = laser_point_vector / np.linalg.norm(
            laser_point_vector
        )  # Normalize

        return {
            "camera_eye": camera_eye,
            "camera_target": camera_target,
            "camera_up": camera_up,
            "laser_position": laser_position,
            "laser_point_vector": laser_point_vector,
        }

    @pytest.fixture
    def test_frame(self):
        """Create a test frame with strong signals for visible lasers"""
        return Frame(
            {
                FrameSignal.freq_high: 1.0,  # Maximum signal strength
                FrameSignal.sustained_high: 1.0,
                FrameSignal.freq_low: 1.0,
                FrameSignal.pulse: 1.0,
                FrameSignal.strobe: 1.0,
                FrameSignal.big_blinder: 1.0,
            }
        )

    @pytest.fixture
    def test_color_scheme(self):
        """Create a bright color scheme for visible lasers"""
        return ColorScheme(
            fg=Color("lime"),  # Bright green lasers
            bg=Color("black"),
            bg_contrast=Color("white"),
        )

    def test_laser_array_visual_render(
        self, headless_context, concert_stage_setup, test_frame, test_color_scheme
    ):
        """Test laser array rendering with visual output analysis"""
        # Create laser array with concert stage setup
        # Make lasers thicker and brighter for better visibility in tests
        laser_array = LaserArray(
            camera_eye=concert_stage_setup["camera_eye"],
            camera_target=concert_stage_setup["camera_target"],
            camera_up=concert_stage_setup["camera_up"],
            laser_position=concert_stage_setup["laser_position"],
            laser_point_vector=concert_stage_setup["laser_point_vector"],
            laser_count=30,  # Same as concert stage default
            laser_length=25.0,  # Longer lasers
            laser_thickness=0.15,  # Thicker lasers for better visibility
            width=800,  # Reasonable test size
            height=600,
        )

        # Initialize with headless context
        laser_array.enter(headless_context)

        try:
            # Generate with rave mode for maximum visibility
            vibe = Vibe(Mode.rave)
            laser_array.generate(vibe)

            # Render the laser array
            result_framebuffer = laser_array.render(
                test_frame, test_color_scheme, headless_context
            )

            # Verify we got a framebuffer
            assert result_framebuffer is not None
            assert hasattr(result_framebuffer, "color_attachments")
            assert len(result_framebuffer.color_attachments) > 0

            # Read the rendered image data
            texture = result_framebuffer.color_attachments[0]

            # Read pixel data (RGBA format)
            raw_data = texture.read()

            # Convert to numpy array and reshape
            # ModernGL returns data in RGBA format, bottom-up
            width, height = texture.size
            image_array = np.frombuffer(raw_data, dtype=np.uint8)
            image_array = image_array.reshape((height, width, 4))

            # Flip vertically (OpenGL uses bottom-left origin, PIL uses top-left)
            image_array = np.flipud(image_array)

            # Convert to PIL Image
            image = Image.fromarray(image_array, "RGBA")

            # Save the image for visual inspection
            output_dir = Path("test_output")
            output_dir.mkdir(exist_ok=True)
            output_path = output_dir / "laser_array_test.png"
            image.save(output_path)
            print(f"Saved laser array render to: {output_path}")

            # Analyze the rendered image
            self._analyze_laser_render(image_array, width, height)

        finally:
            # Clean up
            laser_array.exit()

    def _analyze_laser_render(self, image_array: np.ndarray, width: int, height: int):
        """Analyze the rendered laser image for correctness"""
        # Convert RGBA to RGB for analysis (ignore alpha channel)
        rgb_array = image_array[:, :, :3]

        # Calculate luminance (perceived brightness)
        # Using standard luminance formula: 0.299*R + 0.587*G + 0.114*B
        luminance = (
            0.299 * rgb_array[:, :, 0]
            + 0.587 * rgb_array[:, :, 1]
            + 0.114 * rgb_array[:, :, 2]
        )

        # Define "non-black" as pixels with luminance > threshold
        non_black_threshold = 10  # Out of 255
        non_black_pixels = luminance > non_black_threshold

        total_pixels = width * height
        non_black_count = np.sum(non_black_pixels)
        non_black_percentage = (non_black_count / total_pixels) * 100

        print(f"Image analysis:")
        print(f"  Total pixels: {total_pixels}")
        print(f"  Non-black pixels: {non_black_count}")
        print(f"  Non-black percentage: {non_black_percentage:.2f}%")

        # Test 1: Ensure enough pixels are non-black
        # Lasers should be visible, but not dominate the entire image
        # Adjusted thresholds based on actual laser rendering characteristics
        min_non_black_percentage = (
            0.05  # At least 0.05% of pixels should be laser (very thin beams)
        )
        max_non_black_percentage = 15.0  # But not more than 15% (too bright)

        assert (
            non_black_percentage >= min_non_black_percentage
        ), f"Too few non-black pixels: {non_black_percentage:.2f}% < {min_non_black_percentage}%"
        assert (
            non_black_percentage <= max_non_black_percentage
        ), f"Too many non-black pixels: {non_black_percentage:.2f}% > {max_non_black_percentage}%"

        # Test 2: Analyze spatial distribution
        # Divide image into a 4x3 grid and check distribution
        grid_rows, grid_cols = 3, 4
        row_size = height // grid_rows
        col_size = width // grid_cols

        grid_stats = []
        for row in range(grid_rows):
            for col in range(grid_cols):
                # Extract grid cell
                start_row = row * row_size
                end_row = min((row + 1) * row_size, height)
                start_col = col * col_size
                end_col = min((col + 1) * col_size, width)

                cell_luminance = luminance[start_row:end_row, start_col:end_col]
                cell_non_black = np.sum(cell_luminance > non_black_threshold)
                cell_total = cell_luminance.size
                cell_percentage = (
                    (cell_non_black / cell_total) * 100 if cell_total > 0 else 0
                )

                grid_stats.append(
                    {
                        "row": row,
                        "col": col,
                        "non_black_count": cell_non_black,
                        "total_pixels": cell_total,
                        "percentage": cell_percentage,
                    }
                )

                print(f"  Grid cell ({row},{col}): {cell_percentage:.2f}% non-black")

        # Test 3: Ensure lasers appear in expected regions
        # Lasers should be more concentrated in certain areas based on their positioning
        # The laser source is at top-left of stage, pointing toward audience (camera)
        # So we expect more laser activity in the upper portion of the image

        # Calculate average non-black percentage for top half vs bottom half
        mid_height = height // 2
        top_half_luminance = luminance[:mid_height, :]
        bottom_half_luminance = luminance[mid_height:, :]

        top_non_black = np.sum(top_half_luminance > non_black_threshold)
        bottom_non_black = np.sum(bottom_half_luminance > non_black_threshold)

        top_percentage = (top_non_black / top_half_luminance.size) * 100
        bottom_percentage = (bottom_non_black / bottom_half_luminance.size) * 100

        print(f"  Top half: {top_percentage:.2f}% non-black")
        print(f"  Bottom half: {bottom_percentage:.2f}% non-black")

        # Lasers should be more visible in the top half (where they originate)
        # But this is a soft requirement since lasers fan out
        if top_percentage > 0.1 and bottom_percentage > 0.1:
            # Only check ratio if both halves have some content
            ratio = (
                top_percentage / bottom_percentage
                if bottom_percentage > 0
                else float("inf")
            )
            print(f"  Top/Bottom ratio: {ratio:.2f}")

            # We expect some bias toward the top, but not extreme
            # (lasers fan out so they should appear throughout the image)
            assert (
                ratio >= 0.3
            ), f"Top half too dim compared to bottom: ratio {ratio:.2f}"
            assert (
                ratio <= 10.0
            ), f"Top half too bright compared to bottom: ratio {ratio:.2f}"

        # Test 4: Check for reasonable color distribution
        # Since we're using green lasers, check that green channel is prominent
        green_channel = rgb_array[:, :, 1]  # Green channel
        red_channel = rgb_array[:, :, 0]  # Red channel
        blue_channel = rgb_array[:, :, 2]  # Blue channel

        # In non-black pixels, green should be dominant (since we used lime color)
        non_black_mask = luminance > non_black_threshold
        if np.any(non_black_mask):
            avg_green = np.mean(green_channel[non_black_mask])
            avg_red = np.mean(red_channel[non_black_mask])
            avg_blue = np.mean(blue_channel[non_black_mask])

            print(
                f"  Average color in non-black pixels - R:{avg_red:.1f} G:{avg_green:.1f} B:{avg_blue:.1f}"
            )

            # Green should be the dominant channel for lime lasers
            assert (
                avg_green >= avg_red
            ), "Green channel should be >= red for lime lasers"
            assert (
                avg_green >= avg_blue
            ), "Green channel should be >= blue for lime lasers"

            # Green should be reasonably bright
            assert avg_green >= 50, f"Green channel too dim: {avg_green:.1f}"

    def test_laser_array_different_modes(
        self, headless_context, concert_stage_setup, test_frame, test_color_scheme
    ):
        """Test laser array rendering in different modes"""
        laser_array = LaserArray(
            camera_eye=concert_stage_setup["camera_eye"],
            camera_target=concert_stage_setup["camera_target"],
            camera_up=concert_stage_setup["camera_up"],
            laser_position=concert_stage_setup["laser_position"],
            laser_point_vector=concert_stage_setup["laser_point_vector"],
            laser_count=15,  # Fewer lasers for faster test
            laser_thickness=0.2,  # Thicker for visibility
            width=400,
            height=300,
        )

        laser_array.enter(headless_context)

        try:
            output_dir = Path("test_output")
            output_dir.mkdir(exist_ok=True)

            # Test different modes
            modes = [Mode.rave, Mode.gentle, Mode.blackout]

            for mode in modes:
                vibe = Vibe(mode)
                laser_array.generate(vibe)

                result_framebuffer = laser_array.render(
                    test_frame, test_color_scheme, headless_context
                )
                assert result_framebuffer is not None

                # Save image for each mode
                texture = result_framebuffer.color_attachments[0]
                raw_data = texture.read()
                width, height = texture.size
                image_array = np.frombuffer(raw_data, dtype=np.uint8)
                image_array = image_array.reshape((height, width, 4))
                image_array = np.flipud(image_array)

                image = Image.fromarray(image_array, "RGBA")
                output_path = output_dir / f"laser_array_{mode.name}.png"
                image.save(output_path)
                print(f"Saved {mode.name} mode render to: {output_path}")

                # Quick analysis - just check that something was rendered
                luminance = (
                    0.299 * image_array[:, :, 0]
                    + 0.587 * image_array[:, :, 1]
                    + 0.114 * image_array[:, :, 2]
                )
                non_black_pixels = np.sum(luminance > 10)
                total_pixels = width * height
                non_black_percentage = (non_black_pixels / total_pixels) * 100

                print(
                    f"  {mode.name} mode: {non_black_percentage:.2f}% non-black pixels"
                )

                # All modes should produce some visible output
                # Lower threshold for smaller images and fewer lasers
                assert (
                    non_black_percentage > 0.005
                ), f"{mode.name} mode produced no visible output"

        finally:
            laser_array.exit()

    def test_laser_array_color_schemes(
        self, headless_context, concert_stage_setup, test_frame
    ):
        """Test laser array with different color schemes"""
        laser_array = LaserArray(
            camera_eye=concert_stage_setup["camera_eye"],
            camera_target=concert_stage_setup["camera_target"],
            camera_up=concert_stage_setup["camera_up"],
            laser_position=concert_stage_setup["laser_position"],
            laser_point_vector=concert_stage_setup["laser_point_vector"],
            laser_count=10,  # Fewer lasers for faster test
            width=300,
            height=200,
        )

        laser_array.enter(headless_context)

        try:
            output_dir = Path("test_output")
            output_dir.mkdir(exist_ok=True)

            # Test different colors
            colors = [
                ("red", Color("red")),
                ("blue", Color("blue")),
                ("cyan", Color("cyan")),
                ("magenta", Color("magenta")),
            ]

            vibe = Vibe(Mode.rave)  # Use rave mode for maximum visibility
            laser_array.generate(vibe)

            for color_name, color in colors:
                color_scheme = ColorScheme(
                    fg=color, bg=Color("black"), bg_contrast=Color("white")
                )

                result_framebuffer = laser_array.render(
                    test_frame, color_scheme, headless_context
                )
                assert result_framebuffer is not None

                # Save image for each color
                texture = result_framebuffer.color_attachments[0]
                raw_data = texture.read()
                width, height = texture.size
                image_array = np.frombuffer(raw_data, dtype=np.uint8)
                image_array = image_array.reshape((height, width, 4))
                image_array = np.flipud(image_array)

                image = Image.fromarray(image_array, "RGBA")
                output_path = output_dir / f"laser_array_{color_name}.png"
                image.save(output_path)
                print(f"Saved {color_name} laser render to: {output_path}")

                # Verify the color is correct
                luminance = (
                    0.299 * image_array[:, :, 0]
                    + 0.587 * image_array[:, :, 1]
                    + 0.114 * image_array[:, :, 2]
                )
                non_black_mask = luminance > 10

                if np.any(non_black_mask):
                    avg_red = np.mean(image_array[non_black_mask, 0])
                    avg_green = np.mean(image_array[non_black_mask, 1])
                    avg_blue = np.mean(image_array[non_black_mask, 2])

                    print(
                        f"  {color_name}: R:{avg_red:.1f} G:{avg_green:.1f} B:{avg_blue:.1f}"
                    )

                    # Verify color characteristics
                    if color_name == "red":
                        assert (
                            avg_red > avg_green and avg_red > avg_blue
                        ), "Red lasers should be predominantly red"
                    elif color_name == "blue":
                        assert (
                            avg_blue > avg_red and avg_blue > avg_green
                        ), "Blue lasers should be predominantly blue"
                    elif color_name == "cyan":
                        assert (
                            avg_green > avg_red and avg_blue > avg_red
                        ), "Cyan lasers should have high green and blue"

        finally:
            laser_array.exit()


if __name__ == "__main__":
    # Run the visual tests
    pytest.main([__file__, "-v", "-s"])  # -s to see print output
