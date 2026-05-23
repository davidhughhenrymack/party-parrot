from collections import namedtuple
from parrot.director.color_schemes import (
    scheme_barbie,
    scheme_blue,
    scheme_pride,
    scheme_purple,
    scheme_red,
    scheme_standard,
    scheme_tropical,
    scheme_uv,
    scheme_halloween,
)


Theme = namedtuple("Theme", ["name", "allow_rainbows", "color_scheme"])

themes = [
    Theme("Rave", True, scheme_standard),
    Theme("Pride", True, scheme_pride),
    Theme("Red", False, scheme_red),
    Theme("Blue", False, scheme_blue),
    Theme("Purple", False, scheme_purple),
    Theme("UV", False, scheme_uv),
    Theme("Barbie", False, scheme_barbie),
    Theme("Tropical", True, scheme_tropical),
    Theme("Halloween", False, scheme_halloween),
]


def get_theme_by_name(name):
    for theme in themes:
        if theme.name == name:
            return theme
    raise ValueError(f"Theme {name} not found")
