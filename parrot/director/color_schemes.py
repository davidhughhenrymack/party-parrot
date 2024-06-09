from enum import Enum
import random
from typing import List
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


ColorRelationship = Enum(
    "ColorRelationship", ["analogous", "contrasting", "thick", "mono", "bright"]
)


def generate_random_scheme(
    key: Color,
    methods: List[ColorRelationship] = [
        ColorRelationship.analogous,
        ColorRelationship.thick,
        # ColorRelationship.contrasting,
        # ColorRelationship.mono,
        # ColorRelationship.bright,
    ],
):
    fg = Color(key)
    bg = Color(key)
    bg_contrast = Color(key)

    method = random.choice(methods)

    if method == ColorRelationship.contrasting:
        bg.set_hue((key.hue + 0.5) % 1)
        fg = Color("white")
    elif method == ColorRelationship.thick:
        bg_contrast.set_hue((key.hue + 0.5) % 1)
    elif method == ColorRelationship.analogous:
        bg.set_hue((key.hue + 0.15) % 1)
        bg_contrast.set_hue((key.hue + 0.3) % 1)
    elif method == ColorRelationship.mono:
        fg = Color("white")
    elif method == ColorRelationship.bright:
        bg = Color("white")
        bg_contrast = Color("white")

    return ColorScheme(fg, bg, bg_contrast)


def random_color():
    key = Color("red")
    key.set_hue(random.random())
    return key


scheme_random = [generate_random_scheme(random_color()) for _ in range(10)]

scheme_berlin = [
    generate_random_scheme(
        random.choice([Color("red"), Color("purple")]),
        [ColorRelationship.mono, ColorRelationship.bright],
    )
    for _ in range(10)
]


color_schemes = scheme_standard
