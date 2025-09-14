import pytest
from unittest.mock import Mock, patch
from colorama import Fore, Style
from parrot.utils.color_utils import rgb_to_ansi_color, format_color_scheme


class TestColorUtils:
    def test_rgb_to_ansi_color_white(self):
        """Test RGB to ANSI conversion for white colors."""
        assert rgb_to_ansi_color(255, 255, 255) == Fore.WHITE
        assert rgb_to_ansi_color(220, 220, 220) == Fore.WHITE
        assert rgb_to_ansi_color(201, 201, 201) == Fore.WHITE

    def test_rgb_to_ansi_color_red(self):
        """Test RGB to ANSI conversion for red colors."""
        assert rgb_to_ansi_color(255, 0, 0) == Fore.RED
        assert rgb_to_ansi_color(220, 30, 30) == Fore.RED
        assert rgb_to_ansi_color(201, 49, 49) == Fore.RED

    def test_rgb_to_ansi_color_green(self):
        """Test RGB to ANSI conversion for green colors."""
        assert rgb_to_ansi_color(0, 255, 0) == Fore.GREEN
        assert rgb_to_ansi_color(30, 220, 30) == Fore.GREEN
        assert rgb_to_ansi_color(49, 201, 49) == Fore.GREEN

    def test_rgb_to_ansi_color_blue(self):
        """Test RGB to ANSI conversion for blue colors."""
        assert rgb_to_ansi_color(0, 0, 255) == Fore.BLUE
        assert rgb_to_ansi_color(30, 30, 220) == Fore.BLUE
        assert rgb_to_ansi_color(49, 49, 201) == Fore.BLUE

    def test_rgb_to_ansi_color_yellow(self):
        """Test RGB to ANSI conversion for yellow colors."""
        assert rgb_to_ansi_color(255, 255, 0) == Fore.YELLOW
        assert rgb_to_ansi_color(220, 220, 30) == Fore.YELLOW
        assert rgb_to_ansi_color(201, 201, 49) == Fore.YELLOW

    def test_rgb_to_ansi_color_magenta(self):
        """Test RGB to ANSI conversion for magenta colors."""
        assert rgb_to_ansi_color(255, 0, 255) == Fore.MAGENTA
        assert rgb_to_ansi_color(220, 30, 220) == Fore.MAGENTA
        assert rgb_to_ansi_color(201, 49, 201) == Fore.MAGENTA

    def test_rgb_to_ansi_color_cyan(self):
        """Test RGB to ANSI conversion for cyan colors."""
        assert rgb_to_ansi_color(0, 255, 255) == Fore.CYAN
        assert rgb_to_ansi_color(30, 220, 220) == Fore.CYAN
        assert rgb_to_ansi_color(49, 201, 201) == Fore.CYAN

    def test_rgb_to_ansi_color_no_match(self):
        """Test RGB to ANSI conversion for colors that don't match any category."""
        assert rgb_to_ansi_color(100, 100, 100) == ""
        assert rgb_to_ansi_color(150, 75, 125) == ""
        assert rgb_to_ansi_color(80, 160, 90) == ""

    def test_rgb_to_ansi_color_edge_cases(self):
        """Test RGB to ANSI conversion edge cases."""
        # Test boundary values - the function requires > 200 for high values and < 50 for low values
        assert rgb_to_ansi_color(201, 201, 201) == Fore.WHITE
        assert rgb_to_ansi_color(200, 200, 200) == ""  # Exactly 200 is not > 200

        assert rgb_to_ansi_color(201, 49, 49) == Fore.RED
        assert rgb_to_ansi_color(201, 50, 50) == ""  # 50 is not < 50

        assert rgb_to_ansi_color(49, 201, 49) == Fore.GREEN
        assert rgb_to_ansi_color(50, 201, 50) == ""  # 50 is not < 50

    def test_format_color_scheme_empty(self):
        """Test formatting empty color scheme."""
        mock_scheme = Mock()
        mock_scheme.to_list.return_value = []

        result = format_color_scheme(mock_scheme)
        assert result == ""

    def test_format_color_scheme_single_color(self):
        """Test formatting color scheme with single color."""
        mock_color = Mock()
        mock_color.red = 1.0
        mock_color.green = 0.0
        mock_color.blue = 0.0
        mock_color.__str__ = Mock(return_value="red")

        mock_scheme = Mock()
        mock_scheme.to_list.return_value = [mock_color]

        result = format_color_scheme(mock_scheme)
        expected = f"{Fore.RED}red{Style.RESET_ALL}"
        assert result == expected

    def test_format_color_scheme_multiple_colors(self):
        """Test formatting color scheme with multiple colors."""
        # Red color
        mock_red = Mock()
        mock_red.red = 1.0
        mock_red.green = 0.0
        mock_red.blue = 0.0
        mock_red.__str__ = Mock(return_value="red")

        # Green color
        mock_green = Mock()
        mock_green.red = 0.0
        mock_green.green = 1.0
        mock_green.blue = 0.0
        mock_green.__str__ = Mock(return_value="green")

        # Blue color
        mock_blue = Mock()
        mock_blue.red = 0.0
        mock_blue.green = 0.0
        mock_blue.blue = 1.0
        mock_blue.__str__ = Mock(return_value="blue")

        mock_scheme = Mock()
        mock_scheme.to_list.return_value = [mock_red, mock_green, mock_blue]

        result = format_color_scheme(mock_scheme)
        expected = (
            f"{Fore.RED}red{Style.RESET_ALL} "
            f"{Fore.GREEN}green{Style.RESET_ALL} "
            f"{Fore.BLUE}blue{Style.RESET_ALL}"
        )
        assert result == expected

    def test_format_color_scheme_no_ansi_color(self):
        """Test formatting color scheme with color that has no ANSI equivalent."""
        mock_color = Mock()
        mock_color.red = 0.5
        mock_color.green = 0.5
        mock_color.blue = 0.5
        mock_color.__str__ = Mock(return_value="gray")

        mock_scheme = Mock()
        mock_scheme.to_list.return_value = [mock_color]

        result = format_color_scheme(mock_scheme)
        expected = f"gray{Style.RESET_ALL}"
        assert result == expected

    def test_format_color_scheme_mixed_colors(self):
        """Test formatting color scheme with mix of ANSI and non-ANSI colors."""
        # Red color (has ANSI)
        mock_red = Mock()
        mock_red.red = 1.0
        mock_red.green = 0.0
        mock_red.blue = 0.0
        mock_red.__str__ = Mock(return_value="red")

        # Gray color (no ANSI)
        mock_gray = Mock()
        mock_gray.red = 0.5
        mock_gray.green = 0.5
        mock_gray.blue = 0.5
        mock_gray.__str__ = Mock(return_value="gray")

        mock_scheme = Mock()
        mock_scheme.to_list.return_value = [mock_red, mock_gray]

        result = format_color_scheme(mock_scheme)
        expected = f"{Fore.RED}red{Style.RESET_ALL} " f"gray{Style.RESET_ALL}"
        assert result == expected

    def test_rgb_to_ansi_color_fractional_values(self):
        """Test RGB to ANSI conversion handles fractional RGB values correctly."""
        # The function expects 0-255 range, so 0.8 * 255 = 204 > 200
        assert rgb_to_ansi_color(204, 204, 204) == Fore.WHITE
        assert rgb_to_ansi_color(204, 25, 25) == Fore.RED
        assert rgb_to_ansi_color(25, 204, 25) == Fore.GREEN

    def test_format_color_scheme_color_conversion(self):
        """Test that format_color_scheme correctly converts 0-1 to 0-255 range."""
        mock_color = Mock()
        mock_color.red = 0.8  # Should become 204
        mock_color.green = 0.0  # Should become 0
        mock_color.blue = 0.0  # Should become 0
        mock_color.__str__ = Mock(return_value="red")

        mock_scheme = Mock()
        mock_scheme.to_list.return_value = [mock_color]

        result = format_color_scheme(mock_scheme)
        expected = f"{Fore.RED}red{Style.RESET_ALL}"
        assert result == expected
