from parrot.director.color_schemes import (
    scheme_barbie,
    scheme_blue,
    scheme_pride,
    scheme_purple,
    scheme_red,
    scheme_uv,
)
from parrot.director.themes import get_theme_by_name
from parrot.utils.colour import Color


def test_scheme_pride_is_rgb_primaries():
    assert _scheme_hexes(scheme_pride[0]) == [
        Color("red").hex_l,
        Color("green").hex_l,
        Color("blue").hex_l,
    ]
def test_scheme_pride_is_single_scheme():
    assert len(scheme_pride) == 1


def test_theme_rainbow_flags():
    assert get_theme_by_name("Rainbow").allows_rainbow is True
    assert get_theme_by_name("Rainbow").always_rainbow is True
    assert get_theme_by_name("Tropical").allows_rainbow is True
    assert get_theme_by_name("Tropical").always_rainbow is False
    assert get_theme_by_name("Rave").allows_rainbow is False
    assert get_theme_by_name("Rave").always_rainbow is False


def test_solid_color_schemes_are_single_color():
    assert _scheme_hexes(scheme_red[0]) == [Color("red").hex_l] * 3
    assert _scheme_hexes(scheme_blue[0]) == [Color("blue").hex_l] * 3
    assert _scheme_hexes(scheme_purple[0]) == [Color("purple").hex_l] * 3
    assert _scheme_hexes(scheme_uv[0]) == [Color("#4B0082").hex_l] * 3


def test_scheme_barbie_is_magenta_lavender_indigo():
    assert _scheme_hexes(scheme_barbie[0]) == [
        Color("magenta").hex_l,
        Color("#D8B4F0").hex_l,
        Color("#4B0082").hex_l,
    ]


def _scheme_hexes(scheme):
    return [scheme.fg.hex_l, scheme.bg.hex_l, scheme.bg_contrast.hex_l]
