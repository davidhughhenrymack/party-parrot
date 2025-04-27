from colorama import Fore, Style


def rgb_to_ansi_color(r, g, b):
    """Convert RGB values to approximate ANSI color."""
    if r > 200 and g > 200 and b > 200:
        return Fore.WHITE
    elif r > 200 and g < 50 and b < 50:
        return Fore.RED
    elif r < 50 and g > 200 and b < 50:
        return Fore.GREEN
    elif r < 50 and g < 50 and b > 200:
        return Fore.BLUE
    elif r > 200 and g > 200 and b < 50:
        return Fore.YELLOW
    elif r > 200 and g < 50 and b > 200:
        return Fore.MAGENTA
    elif r < 50 and g > 200 and b > 200:
        return Fore.CYAN
    return ""


def format_color_scheme(scheme):
    """Format a color scheme with ANSI colors."""
    colors = scheme.to_list()
    colored_colors = []
    for color in colors:
        # Convert RGB values from 0-1 to 0-255
        r = int(color.red * 255)
        g = int(color.green * 255)
        b = int(color.blue * 255)
        ansi_color = rgb_to_ansi_color(r, g, b)
        colored_colors.append(f"{ansi_color}{color}{Style.RESET_ALL}")
    return " ".join(colored_colors)
