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
    """Pick three distinct named pool colors, shuffle order, build a ``ColorScheme``.

    Uses :func:`random.sample` then :func:`random.shuffle` so fg / bg /
    ``bg_contrast`` are a random permutation of three colors from
    ``available_colors``.
    """
    names = random.sample(available_colors, 3)
    random.shuffle(names)
    return ColorScheme(Color(names[0]), Color(names[1]), Color(names[2]))


scheme_pride = [generate_pride_scheme() for _ in range(10)]

# Red / purple / magenta club palette (was generated from red–purple keys + mono/bright).
scheme_berlin = [
    ColorScheme(Color("white"), Color("red"), Color("purple")),
    ColorScheme(Color("white"), Color("purple"), Color("red")),
    ColorScheme(Color("red"), Color("purple"), Color("purple")),
    ColorScheme(Color("purple"), Color("red"), Color("magenta")),
    ColorScheme(Color("white"), Color("magenta"), Color("purple")),
    ColorScheme(Color("magenta"), Color("purple"), Color("red")),
    ColorScheme(Color("red"), Color("red"), Color("purple")),
    ColorScheme(Color("purple"), Color("purple"), Color("blue")),
    ColorScheme(Color("white"), Color("red"), Color("red")),
    ColorScheme(Color("blue"), Color("purple"), Color("magenta")),
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
