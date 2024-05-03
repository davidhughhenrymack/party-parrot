from typing import List
from parrot.utils.colour import Color
from .math import clamp
from parrot.utils.lerp import lerp


def lerp_color(a: Color, b: Color, t: float) -> Color:
    return Color(
        rgb=(lerp(a.red, b.red, t), lerp(a.green, b.green, t), lerp(a.blue, b.blue, t))
    )


def color_distance(a: Color, b: Color) -> float:
    # Hue distance plus saturation distance plus value distance
    return (
        abs(a.hue - b.hue)
        + abs(a.saturation - b.saturation)
        + abs(a.luminance - b.luminance)
    )


def dim_color(color: Color, dimmer: float) -> Color:
    dimmer = clamp(dimmer, 0, 1)
    return Color(rgb=(color.red * dimmer, color.green * dimmer, color.blue * dimmer))


def render_color_components(
    components: List[Color],
    target_color: Color,
    dimmer: int,
    values: List[int],
    address=0,
    count=2,
):
    distances = [
        (idx, color, color_distance(target_color, color))
        for idx, color in enumerate(components)
    ]
    distances = sorted(
        [i for i in distances if i[2] < 1], key=lambda i: i[2], reverse=True
    )

    distances = distances[-count:]

    for i in range(len(components)):
        values[address + i] = 0

    for idx, _, dist in distances:
        dn = (3 - dist) / 3
        dim = dimmer / 255
        values[address + idx] = int(dn * dim * 255)


def color_to_rgbw(color: Color):
    if color.get_saturation() < 0.1:
        return (0, 0, 0, color.luminance * 255)
    else:
        return (color.red * 255, color.green * 255, color.blue * 255, 0)
