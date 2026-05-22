from parrot.director.color_schemes import (
    PRIDE_MIN_HUE_DISTANCE,
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


def test_generate_pride_scheme_orders_by_rgb_sum_descending():
    for _ in range(200):
        s = generate_pride_scheme()
        fg_sum = sum(s.fg.rgb)
        bg_sum = sum(s.bg.rgb)
        bc_sum = sum(s.bg_contrast.rgb)
        assert fg_sum >= bg_sum >= bc_sum


def test_generate_pride_scheme_enforces_minimum_hue_distance():
    for _ in range(200):
        s = generate_pride_scheme()
        colors = (s.fg, s.bg, s.bg_contrast)
        for i, color in enumerate(colors):
            for other in colors[i + 1:]:
                distance = min(abs(color.hue - other.hue), 1.0 - abs(color.hue - other.hue))
                assert distance >= PRIDE_MIN_HUE_DISTANCE


def test_scheme_pride_enforces_minimum_hue_distance():
    for s in scheme_pride:
        colors = (s.fg, s.bg, s.bg_contrast)
        for i, color in enumerate(colors):
            for other in colors[i + 1:]:
                distance = min(abs(color.hue - other.hue), 1.0 - abs(color.hue - other.hue))
                assert distance >= PRIDE_MIN_HUE_DISTANCE


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
