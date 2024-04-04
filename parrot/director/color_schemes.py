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

key = Color("red")
key.set_hue(random.random())


def generate_random_scheme():
    fg = Color(key)
    bg = Color(key)
    bg_contrast = Color(key)

    method = random.choice(["analogous", "contrasting", "thick", "mono", "bright"])

    match method:
        case "contrasting":
            bg.set_hue((key.hue + 0.5) % 1)
            fg = Color("white")
        case "thick":
            bg_contrast.set_hue((key.hue + 0.5) % 1)
        case "analogous":
            bg.set_hue((key.hue + 0.15) % 1)
            bg_contrast.set_hue((key.hue + 0.3) % 1)
        case "mono":
            fg = Color("white")
        case "bright":
            bg = Color("white")
            bg_contrast = Color("white")

    return ColorScheme(fg, bg, bg_contrast)


scheme_random = [generate_random_scheme() for _ in range(10)]


color_schemes = scheme_random
