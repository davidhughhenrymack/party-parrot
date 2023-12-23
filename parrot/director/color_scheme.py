from parrot.utils.colour import Color


class ColorScheme:
    def __init__(self, fg: Color, bg: Color, bg_contrast: Color):
        self.fg = fg
        self.bg = bg
        self.bg_contrast = bg_contrast
