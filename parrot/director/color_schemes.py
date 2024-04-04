import random
from parrot.director.color_scheme import ColorScheme
from parrot.utils.colour import Color

available_colors = [
    "red",
    "green",
    "blue",
    "cyan",
    "magenta",
    "yellow",
    "white",
    "purple",
    "orange",
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

scheme_random = [
    ColorScheme(
        Color(random.choice(available_colors)),
        Color(random.choice(available_colors)),
        Color(random.choice(available_colors)),
    )
    for _ in range(10)
]


color_schemes = scheme_random
