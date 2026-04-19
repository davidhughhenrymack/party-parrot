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


def _is_white(color: Color) -> bool:
    """True for fully-desaturated near-white colors.

    Using hex equality is too brittle (hue-rotating a white color still leaves
    it white but may produce `#fefefe`-style rounding). A saturation/luminance
    check matches every visually-white result that comes out of the Color
    library.
    """
    return color.saturation < 0.05 and color.luminance > 0.95


def _enforce_at_most_one_white(scheme: ColorScheme) -> ColorScheme:
    """Return a `ColorScheme` with at most one white slot.

    Pride uses this so schemes never get washed out to a monochrome white rig.
    If two or three slots land on white, the extras are replaced with a
    saturated, randomly-hued color so the rig still reads as "pride" —
    colorful — rather than "all spotlights blanked to white".
    """
    slots = [scheme.fg, scheme.bg, scheme.bg_contrast]
    white_indices = [i for i, c in enumerate(slots) if _is_white(c)]
    if len(white_indices) <= 1:
        return scheme
    for i in white_indices[1:]:
        slots[i] = random_color()
    return ColorScheme(slots[0], slots[1], slots[2])


scheme_random = [
    _enforce_at_most_one_white(
        generate_random_scheme(Color(random.choice(available_colors)))
    )
    for _ in range(10)
]

scheme_berlin = [
    generate_random_scheme(
        random.choice([Color("red"), Color("purple")]),
        [ColorRelationship.mono, ColorRelationship.bright],
    )
    for _ in range(10)
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
