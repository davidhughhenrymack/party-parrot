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

scheme_pride = [
    ColorScheme(
        Color("red"),
        Color("green"),
        Color("blue"),
    ),
]

scheme_red = [
    ColorScheme(Color("red"), Color("red"), Color("red")),
]

scheme_blue = [
    ColorScheme(Color("blue"), Color("blue"), Color("blue")),
]

scheme_purple = [
    ColorScheme(Color("purple"), Color("purple"), Color("purple")),
]

scheme_uv = [
    ColorScheme(Color("#4B0082"), Color("#4B0082"), Color("#4B0082")),
]

scheme_barbie = [
    ColorScheme(Color("magenta"), Color("#D8B4F0"), Color("#4B0082")),
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
