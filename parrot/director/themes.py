from collections import namedtuple
from parrot.director.color_schemes import (
    scheme_berlin,
    scheme_random,
    scheme_standard,
    scheme_tropical,
)


Theme = namedtuple("Theme", ["name", "allow_rainbows", "color_scheme"])

themes = [
    Theme("Rave", True, scheme_standard),
    Theme("Berlin", False, scheme_berlin),
    Theme("Pride", True, scheme_random),
    Theme("Tropical", True, scheme_tropical),
]


def get_theme_by_name(name):
    for theme in themes:
        if theme.name == name:
            return theme
    raise ValueError(f"Theme {name} not found")
