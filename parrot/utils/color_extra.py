from parrot.utils.colour import Color
from parrot.utils.lerp import lerp


def lerp_color(a: Color, b: Color, t: float) -> Color:
    return Color(
        rgb=(lerp(a.red, b.red, t), lerp(a.green, b.green, t), lerp(a.blue, b.blue, t))
    )
