from parrot.director.color_schemes import (
    generate_pride_scheme,
    scheme_berlin,
    scheme_pride,
)
from parrot.utils.colour import Color


def test_generate_pride_scheme_is_three_distinct_pool_colors():
    for _ in range(100):
        s = generate_pride_scheme()
        hexes = (s.fg.hex_l, s.bg.hex_l, s.bg_contrast.hex_l)
        assert len(set(hexes)) == 3


def test_generate_pride_scheme_allows_rainbow():
    assert generate_pride_scheme().allows_rainbow is True


def test_scheme_pride_length_matches_other_themes():
    assert len(scheme_pride) == 10


def test_scheme_berlin_length_matches_other_themes():
    assert len(scheme_berlin) == 10


def test_scheme_berlin_is_monochromatic():
    """Each Berlin option uses at most one non-white color (repeats + white ok)."""
    white_hex = Color("white").hex_l.lower()

    def non_white_hexes(scheme):
        return {
            c.hex_l.lower()
            for c in (scheme.fg, scheme.bg, scheme.bg_contrast)
            if c.hex_l.lower() != white_hex
        }

    for s in scheme_berlin:
        assert len(non_white_hexes(s)) <= 1
