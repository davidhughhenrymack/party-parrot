from parrot.utils.colour import Color
from parrot.utils.lerp import Lerpable
from parrot.utils.color_extra import lerp_color


class ColorScheme(Lerpable):
    def __init__(self, fg: Color, bg: Color, bg_contrast: Color):
        self.fg = fg
        self.bg = bg
        self.bg_contrast = bg_contrast

    def lerp(self, other, t):
        return ColorScheme(
            lerp_color(self.fg, other.fg, t),
            lerp_color(self.bg, other.bg, t),
            lerp_color(self.bg_contrast, other.bg_contrast, t),
        )

    def __str__(self) -> str:
        return f"ColorScheme({self.fg}, {self.bg}, {self.bg_contrast})"
