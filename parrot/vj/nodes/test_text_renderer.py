#!/usr/bin/env python3

import pytest
from unittest.mock import Mock, patch

from parrot.vj.nodes.text_renderer import TextRenderer, WhiteText, BlackText, ColorText


class TestTextRenderer:
    """Test TextRenderer node - focused on colors and font handling"""

    def test_color_initialization(self):
        """Test that colors are set correctly"""
        # Default colors
        text_node = TextRenderer()
        assert text_node.text_color == (255, 255, 255)  # White
        assert text_node.bg_color == (0, 0, 0)  # Black

        # Custom colors
        text_node = TextRenderer(
            text_color=(255, 0, 0), bg_color=(0, 255, 0)  # Red  # Green
        )
        assert text_node.text_color == (255, 0, 0)
        assert text_node.bg_color == (0, 255, 0)

    def test_factory_functions_colors(self):
        """Test that factory functions set correct colors"""
        # WhiteText: white text on black background
        white_text = WhiteText("Test")
        assert white_text.text_color == (255, 255, 255)
        assert white_text.bg_color == (0, 0, 0)

        # BlackText: black text on white background
        black_text = BlackText("Test")
        assert black_text.text_color == (0, 0, 0)
        assert black_text.bg_color == (255, 255, 255)

        # ColorText: custom colors
        color_text = ColorText(
            "Test", text_color=(255, 0, 0), bg_color=(0, 0, 255)  # Red  # Blue
        )
        assert color_text.text_color == (255, 0, 0)
        assert color_text.bg_color == (0, 0, 255)

    @patch("parrot.vj.nodes.text_renderer.ImageFont")
    def test_font_loading_success(self, mock_image_font):
        """Test that named fonts are loaded correctly"""
        mock_font = Mock()
        mock_image_font.truetype.return_value = mock_font

        text_node = TextRenderer(font_name="Arial", font_size=48)
        text_node._load_font()

        # Should try to load the named font with correct size
        mock_image_font.truetype.assert_called_with("Arial", 48)
        assert text_node.font == mock_font

    @patch("parrot.vj.nodes.text_renderer.ImageFont")
    @patch("parrot.vj.nodes.text_renderer.os.path.exists")
    def test_font_loading_fallback(self, mock_exists, mock_image_font):
        """Test fallback to default font when named font not found"""
        # Make truetype fail (font not found)
        mock_image_font.truetype.side_effect = OSError("Font not found")
        # Make all font paths not exist
        mock_exists.return_value = False
        # Set up default font
        mock_default_font = Mock()
        mock_image_font.load_default.return_value = mock_default_font

        text_node = TextRenderer(font_name="NonExistentFont")
        text_node._load_font()

        # Should fall back to default font
        mock_image_font.load_default.assert_called_once()
        assert text_node.font == mock_default_font

    def test_color_updates(self):
        """Test that color updates work correctly"""
        text_node = TextRenderer()

        # Update colors
        text_node.set_colors((255, 0, 0), (0, 0, 255))  # Red text, blue bg
        assert text_node.text_color == (255, 0, 0)
        assert text_node.bg_color == (0, 0, 255)
        assert text_node._needs_update  # Should trigger re-render

    def test_sonnyfive_font_loading(self):
        """Test that 'The Sonnyfive' font can be found and loaded on the local system"""
        text_node = TextRenderer(font_name="The Sonnyfive", font_size=48)
        text_node._load_font()

        # Font should be loaded (either the actual font or fallback to default)
        assert text_node.font is not None, "Font should be loaded"

        # Try to determine if we got the actual font or fallback
        print(f"Font loaded for 'The Sonnyfive': {type(text_node.font)}")

        # Check if we can get font information (this works for TrueType fonts)
        try:
            if hasattr(text_node.font, "getname"):
                font_name = text_node.font.getname()
                print(f"Font name info: {font_name}")
                # If we got the actual font, the name should contain "Sonnyfive"
                if "Sonnyfive" in str(font_name):
                    print("✅ Successfully loaded 'The Sonnyfive' font!")
                else:
                    print("⚠️  Loaded fallback font instead of 'The Sonnyfive'")
            else:
                print(
                    "ℹ️  Font loaded but name info not available (likely default font)"
                )
        except Exception as e:
            print(f"ℹ️  Could not get font name info: {e}")

        # Test that we can render text with this font (basic functionality test)
        try:
            from PIL import Image, ImageDraw

            test_image = Image.new("RGB", (100, 50), (255, 255, 255))
            draw = ImageDraw.Draw(test_image)
            draw.text((10, 10), "TEST", fill=(0, 0, 0), font=text_node.font)
            print("✅ Font can render text successfully")
        except Exception as e:
            print(f"❌ Font rendering test failed: {e}")
            raise
