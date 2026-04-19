from parrot.director.color_schemes import (
    generate_pride_scheme,
    scheme_berlin,
    scheme_pride,
)


def test_generate_pride_scheme_is_three_distinct_pool_colors():
    for _ in range(100):
        s = generate_pride_scheme()
        hexes = (s.fg.hex_l, s.bg.hex_l, s.bg_contrast.hex_l)
        assert len(set(hexes)) == 3


def test_scheme_pride_length_matches_other_themes():
    assert len(scheme_pride) == 10


def test_scheme_berlin_length_matches_other_themes():
    assert len(scheme_berlin) == 10
