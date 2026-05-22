import pytest

from parrot.utils.color_extra import color_distance, hue_distance
from parrot.utils.colour import Color


def test_hue_distance_wraps_around_red_boundary():
    assert hue_distance(0.99, 0.01) == pytest.approx(0.02)


def test_color_distance_treats_wrapped_red_as_close():
    target = Color("red")
    target.set_hue(0.99)

    assert color_distance(target, Color("red")) < color_distance(target, Color("magenta"))


def test_color_distance_prefers_hue_over_luminance_for_saturated_colors():
    target = Color("green")

    assert color_distance(target, Color("lime")) < color_distance(target, Color("yellow"))
