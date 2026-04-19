import random

from parrot.director.color_scheme import ColorScheme
from parrot.director.color_schemes import (
    _enforce_at_most_one_white,
    _is_white,
    generate_random_scheme,
)
from parrot.utils.colour import Color


def _white_count(scheme: ColorScheme) -> int:
    return sum(1 for c in scheme.to_list() if _is_white(c))


def test_enforce_at_most_one_white_leaves_colorful_scheme_alone():
    scheme = ColorScheme(Color("red"), Color("blue"), Color("purple"))
    result = _enforce_at_most_one_white(scheme)
    assert result.fg.get_hex_l() == scheme.fg.get_hex_l()
    assert result.bg.get_hex_l() == scheme.bg.get_hex_l()
    assert result.bg_contrast.get_hex_l() == scheme.bg_contrast.get_hex_l()


def test_enforce_at_most_one_white_replaces_extra_whites():
    scheme = ColorScheme(Color("white"), Color("white"), Color("white"))
    result = _enforce_at_most_one_white(scheme)
    assert _white_count(result) <= 1
    assert _is_white(result.fg), "first slot should be preserved as the one white"


def test_pride_random_generation_never_has_more_than_one_white():
    """`generate_random_scheme` with a white key produces all-white schemes;
    Pride wraps it in `_enforce_at_most_one_white` to cap that. This test
    simulates the Pride path directly so we catch regressions even if the
    module-level `scheme_random` list is regenerated with lucky seeds."""
    rng = random.Random(0)
    bad_keys = 0
    for _ in range(50):
        # Force the white edge case — rotating hue on white is a no-op, so
        # the raw generator returns an all-white scheme.
        raw = generate_random_scheme(Color("white"))
        assert _white_count(raw) >= 2, "test precondition: white key -> many whites"
        capped = _enforce_at_most_one_white(raw)
        assert _white_count(capped) <= 1
        bad_keys += 1
        rng.random()
    assert bad_keys == 50
