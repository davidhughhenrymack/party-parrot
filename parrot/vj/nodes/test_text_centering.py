#!/usr/bin/env python3

import pytest
import numpy as np
import moderngl as mgl
from PIL import Image, ImageDraw, ImageFont

from parrot.vj.nodes.text_renderer import TextRenderer
from parrot.director.frame import Frame, FrameSignal
from parrot.director.color_scheme import ColorScheme
from parrot.utils.colour import Color


class TestTextCentering:
    """Test that text is properly centered both horizontally and vertically"""

    @pytest.fixture
    def gl_context(self):
        """Create a real OpenGL context for testing"""
        try:
            context = mgl.create_context(standalone=True, backend="egl")
            yield context
        except Exception:
            try:
                context = mgl.create_context(standalone=True)
                yield context
            except Exception as e:
                raise RuntimeError(f"OpenGL context creation failed: {e}")

    @pytest.fixture
    def color_scheme(self):
        """Create a color scheme"""
        return ColorScheme(
            fg=Color("red"), bg=Color("black"), bg_contrast=Color("white")
        )

    def test_text_is_centered(self, gl_context, color_scheme):
        """Test that text is properly centered in the canvas"""
        # Use a simple single character for easier analysis
        text_node = TextRenderer(
            text="A",
            font_size=72,
            width=200,
            height=200,
            text_color=(255, 255, 255),  # White text
            bg_color=(0, 0, 0),  # Black background
        )

        text_node.enter(gl_context)

        try:
            frame = Frame({FrameSignal.freq_low: 0.0})
            result_framebuffer = text_node.render(frame, color_scheme, gl_context)

            fb_data = result_framebuffer.read()
            pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape((200, 200, 3))

            # Find all white pixels (text pixels)
            white_pixels = np.all(pixels == [255, 255, 255], axis=2)
            text_positions = np.where(white_pixels)

            # Should have some text pixels
            assert len(text_positions[0]) > 0, "Should have text pixels"

            # Calculate the bounding box of the text
            min_y, max_y = np.min(text_positions[0]), np.max(text_positions[0])
            min_x, max_x = np.min(text_positions[1]), np.max(text_positions[1])

            # Calculate the center of the text
            text_center_y = (min_y + max_y) / 2
            text_center_x = (min_x + max_x) / 2

            # Canvas center
            canvas_center_y = 200 / 2  # 100
            canvas_center_x = 200 / 2  # 100

            print(f"Text center: ({text_center_x:.1f}, {text_center_y:.1f})")
            print(f"Canvas center: ({canvas_center_x:.1f}, {canvas_center_y:.1f})")

            # Allow some tolerance for centering (within 10% of canvas size)
            tolerance = 20  # 10% of 200

            # Check horizontal centering
            horizontal_offset = abs(text_center_x - canvas_center_x)
            assert horizontal_offset <= tolerance, (
                f"Text not horizontally centered. "
                f"Text center X: {text_center_x:.1f}, Canvas center X: {canvas_center_x:.1f}, "
                f"Offset: {horizontal_offset:.1f} (tolerance: {tolerance})"
            )

            # Check vertical centering
            vertical_offset = abs(text_center_y - canvas_center_y)
            assert vertical_offset <= tolerance, (
                f"Text not vertically centered. "
                f"Text center Y: {text_center_y:.1f}, Canvas center Y: {canvas_center_y:.1f}, "
                f"Offset: {vertical_offset:.1f} (tolerance: {tolerance})"
            )

            print("✓ Text is properly centered!")

        finally:
            text_node.exit()

    def test_multiline_text_centering(self, gl_context, color_scheme):
        """Test that multiline text is properly centered"""
        text_node = TextRenderer(
            text="HELLO\nWORLD",
            font_size=48,
            width=300,
            height=200,
            text_color=(255, 255, 255),  # White text
            bg_color=(0, 0, 0),  # Black background
        )

        text_node.enter(gl_context)

        try:
            frame = Frame({FrameSignal.freq_low: 0.0})
            result_framebuffer = text_node.render(frame, color_scheme, gl_context)

            fb_data = result_framebuffer.read()
            pixels = np.frombuffer(fb_data, dtype=np.uint8).reshape((200, 300, 3))

            # Find all white pixels (text pixels)
            white_pixels = np.all(pixels == [255, 255, 255], axis=2)
            text_positions = np.where(white_pixels)

            # Should have some text pixels
            assert len(text_positions[0]) > 0, "Should have text pixels"

            # Calculate the bounding box of the text
            min_y, max_y = np.min(text_positions[0]), np.max(text_positions[0])
            min_x, max_x = np.min(text_positions[1]), np.max(text_positions[1])

            # Calculate the center of the text
            text_center_y = (min_y + max_y) / 2
            text_center_x = (min_x + max_x) / 2

            # Canvas center
            canvas_center_y = 200 / 2  # 100
            canvas_center_x = 300 / 2  # 150

            print(f"Multiline text center: ({text_center_x:.1f}, {text_center_y:.1f})")
            print(f"Canvas center: ({canvas_center_x:.1f}, {canvas_center_y:.1f})")

            # Allow some tolerance for centering
            tolerance_x = 30  # 10% of 300
            tolerance_y = 20  # 10% of 200

            # Check horizontal centering
            horizontal_offset = abs(text_center_x - canvas_center_x)
            assert horizontal_offset <= tolerance_x, (
                f"Multiline text not horizontally centered. "
                f"Text center X: {text_center_x:.1f}, Canvas center X: {canvas_center_x:.1f}, "
                f"Offset: {horizontal_offset:.1f} (tolerance: {tolerance_x})"
            )

            # Check vertical centering
            vertical_offset = abs(text_center_y - canvas_center_y)
            assert vertical_offset <= tolerance_y, (
                f"Multiline text not vertically centered. "
                f"Text center Y: {text_center_y:.1f}, Canvas center Y: {canvas_center_y:.1f}, "
                f"Offset: {vertical_offset:.1f} (tolerance: {tolerance_y})"
            )

            print("✓ Multiline text is properly centered!")

        finally:
            text_node.exit()

    def test_pil_centering_directly(self):
        """Test PIL centering logic directly without OpenGL"""
        width, height = 400, 200
        text = "TEST"
        font_size = 48

        # Load font
        try:
            font = ImageFont.truetype("Arial", font_size)
        except (OSError, IOError):
            font = ImageFont.load_default()

        # Create image and draw
        image = Image.new("RGB", (width, height), (0, 0, 0))
        draw = ImageDraw.Draw(image)

        # Draw text centered using anchor parameter
        center_x = width // 2
        center_y = height // 2
        draw.text(
            (center_x, center_y), text, fill=(255, 255, 255), font=font, anchor="mm"
        )

        # Convert to numpy for analysis
        pixels = np.array(image)

        # Find all white pixels (text pixels)
        white_pixels = np.all(pixels == [255, 255, 255], axis=2)
        text_positions = np.where(white_pixels)

        # Should have some text pixels
        assert len(text_positions[0]) > 0, "Should have text pixels"

        # Calculate the bounding box of the text
        min_y, max_y = np.min(text_positions[0]), np.max(text_positions[0])
        min_x, max_x = np.min(text_positions[1]), np.max(text_positions[1])

        # Calculate the center of the text
        text_center_y = (min_y + max_y) / 2
        text_center_x = (min_x + max_x) / 2

        # Canvas center
        canvas_center_y = height / 2
        canvas_center_x = width / 2

        print(
            f"PIL direct test - Text center: ({text_center_x:.1f}, {text_center_y:.1f})"
        )
        print(
            f"PIL direct test - Canvas center: ({canvas_center_x:.1f}, {canvas_center_y:.1f})"
        )

        # Allow some tolerance for centering
        tolerance_x = width * 0.1  # 10% of width
        tolerance_y = height * 0.1  # 10% of height

        # Check horizontal centering
        horizontal_offset = abs(text_center_x - canvas_center_x)
        assert horizontal_offset <= tolerance_x, (
            f"PIL direct: Text not horizontally centered. "
            f"Text center X: {text_center_x:.1f}, Canvas center X: {canvas_center_x:.1f}, "
            f"Offset: {horizontal_offset:.1f} (tolerance: {tolerance_x})"
        )

        # Check vertical centering
        vertical_offset = abs(text_center_y - canvas_center_y)
        assert vertical_offset <= tolerance_y, (
            f"PIL direct: Text not vertically centered. "
            f"Text center Y: {text_center_y:.1f}, Canvas center Y: {canvas_center_y:.1f}, "
            f"Offset: {vertical_offset:.1f} (tolerance: {tolerance_y})"
        )

        print("✓ PIL direct centering works correctly!")
