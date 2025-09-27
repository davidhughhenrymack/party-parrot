from collections import namedtuple
from parrot.director.color_schemes import (
    scheme_berlin,
    scheme_random,
    scheme_standard,
    scheme_tropical,
    scheme_halloween,
)


Theme = namedtuple("Theme", ["name", "allow_rainbows", "color_scheme"])

themes = [
    Theme("Rave", True, scheme_standard),
    Theme("Pride", True, scheme_random),
    Theme("Berlin", False, scheme_berlin),
    Theme("Tropical", True, scheme_tropical),
    Theme("Halloween", False, scheme_halloween),
]


def get_theme_by_name(name):
    for theme in themes:
        if theme.name == name:
            return theme
    raise ValueError(f"Theme {name} not found")
