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
