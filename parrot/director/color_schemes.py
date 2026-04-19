import random
from parrot.director.color_scheme import ColorScheme
from parrot.utils.colour import Color

available_colors = [
    "red",
    "orange",
    "yellow",
    "green",
    "blue",
    "cyan",
    "magenta",
    "purple",
    "white",
]

scheme_tropical = [
    ColorScheme(Color("green"), Color("blue"), Color("blue")),
    ColorScheme(Color("white"), Color("blue"), Color("purple")),
    ColorScheme(Color("white"), Color("green"), Color("purple")),
    ColorScheme(Color("white"), Color("green"), Color("yellow")),
    ColorScheme(Color("magenta"), Color("blue"), Color("purple")),
    ColorScheme(Color("blue"), Color("purple"), Color("purple")),
]

scheme_standard = [
    ColorScheme(Color("green"), Color("blue"), Color("blue")),
    ColorScheme(Color("white"), Color("blue"), Color("purple")),
    ColorScheme(Color("white"), Color("red"), Color("red")),
    ColorScheme(Color("white"), Color("red"), Color("purple")),
    ColorScheme(Color("red"), Color("blue"), Color("blue")),
    ColorScheme(Color("magenta"), Color("blue"), Color("purple")),
    ColorScheme(Color("blue"), Color("purple"), Color("purple")),
]


def generate_pride_scheme() -> ColorScheme:
    """Pick three distinct named pool colors, build a ``ColorScheme``.

    Uses :func:`random.sample` for the triple, then assigns fg / bg /
    ``bg_contrast`` in descending order of total RGB (``sum(color.rgb)``), so
    brighter colors (e.g. white) are foreground and darker hues land in bg /
    contrast roles.
    """
    names = random.sample(available_colors, 3)
    colors = [Color(n) for n in names]
    ordered = sorted(colors, key=lambda c: sum(c.rgb), reverse=True)
    return ColorScheme(
        ordered[0],
        ordered[1],
        ordered[2],
        allows_rainbow=True,
    )


scheme_pride = [generate_pride_scheme() for _ in range(10)]

# Red / purple / magenta club palette: each scheme uses at most one chromatic hue
# plus white (repeats of that hue or white in fg / bg / bg_contrast).
scheme_berlin = [
    ColorScheme(Color("white"), Color("red"), Color("red")),
    ColorScheme(Color("red"), Color("red"), Color("red")),
    ColorScheme(Color("white"), Color("blue"), Color("blue")),
]

scheme_halloween = [
    ColorScheme(Color("purple"), Color("purple"), Color("green")),
    ColorScheme(Color("white"), Color("red"), Color("purple")),
    ColorScheme(Color("green"), Color("blue"), Color("purple")),
    ColorScheme(Color("purple"), Color("blue"), Color("green")),
    ColorScheme(Color("white"), Color("red"), Color("red")),
    ColorScheme(Color("white"), Color("purple"), Color("blue")),
]


color_schemes = scheme_standard
