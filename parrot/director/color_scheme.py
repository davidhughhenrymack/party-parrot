from parrot.utils.colour import Color
from parrot.utils.lerp import Lerpable
from parrot.utils.color_extra import lerp_color


class ColorScheme(Lerpable):
    def __init__(
        self,
        fg: Color,
        bg: Color,
        bg_contrast: Color,
        *,
        allows_rainbow: bool = False,
    ):
        self.fg = fg
        self.bg = bg
        self.bg_contrast = bg_contrast
        self.allows_rainbow = allows_rainbow

    def lerp(self, other, t):
        allows_rainbow = self.allows_rainbow if t < 0.5 else other.allows_rainbow
        return ColorScheme(
            lerp_color(self.fg, other.fg, t),
            lerp_color(self.bg, other.bg, t),
            lerp_color(self.bg_contrast, other.bg_contrast, t),
            allows_rainbow=allows_rainbow,
        )

    def to_list(self):
        return [self.fg, self.bg, self.bg_contrast]

    def __str__(self) -> str:
        return f"ColorScheme({self.fg}, {self.bg}, {self.bg_contrast}, allows_rainbow={self.allows_rainbow})"

    @classmethod
    def from_list(cls, list, *, allows_rainbow: bool = False):
        return cls(list[0], list[1], list[2], allows_rainbow=allows_rainbow)
