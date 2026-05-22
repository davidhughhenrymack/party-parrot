import random
from parrot.director.color_scheme import ColorScheme
from parrot.utils.colour import Color

available_colors = [
    "red",
    "orange",
    "yellow",
    "green",
    "blue",
    "cyan",
    "magenta",
    "purple",
    "white",
]

PRIDE_MIN_HUE_DISTANCE = 0.12
pride_colors = [name for name in available_colors if name != "white"]

scheme_tropical = [
    ColorScheme(Color("green"), Color("blue"), Color("blue")),
    ColorScheme(Color("white"), Color("blue"), Color("purple")),
    ColorScheme(Color("white"), Color("green"), Color("purple")),
    ColorScheme(Color("white"), Color("green"), Color("yellow")),
    ColorScheme(Color("magenta"), Color("blue"), Color("purple")),
    ColorScheme(Color("blue"), Color("purple"), Color("purple")),
]

scheme_standard = [
    ColorScheme(Color("green"), Color("blue"), Color("blue")),
    ColorScheme(Color("white"), Color("blue"), Color("purple")),
    ColorScheme(Color("white"), Color("red"), Color("red")),
    ColorScheme(Color("white"), Color("red"), Color("purple")),
    ColorScheme(Color("red"), Color("blue"), Color("blue")),
    ColorScheme(Color("magenta"), Color("blue"), Color("purple")),
    ColorScheme(Color("blue"), Color("purple"), Color("purple")),
]


def generate_pride_scheme() -> ColorScheme:
    """Pick three distinct named pool colors, build a ``ColorScheme``.

    Uses :func:`random.sample` for the triple, then assigns fg / bg /
    ``bg_contrast`` in descending order of total RGB (``sum(color.rgb)``), so
    brighter colors (e.g. white) are foreground and darker hues land in bg /
    contrast roles.
    """
    names = _sample_pride_color_names()
    colors = [Color(n) for n in names]
    ordered = sorted(colors, key=lambda c: sum(c.rgb), reverse=True)
    return ColorScheme(
        ordered[0],
        ordered[1],
        ordered[2],
        allows_rainbow=True,
    )


def _hue_distance(a: Color, b: Color) -> float:
    raw = abs(float(a.hue) - float(b.hue))
    return min(raw, 1.0 - raw)


def _hues_are_spaced(colors: list[Color]) -> bool:
    for i, color in enumerate(colors):
        for other in colors[i + 1:]:
            if _hue_distance(color, other) < PRIDE_MIN_HUE_DISTANCE:
                return False
    return True


def _sample_pride_color_names() -> list[str]:
    for _ in range(100):
        names = random.sample(pride_colors, 3)
        if _hues_are_spaced([Color(name) for name in names]):
            return names
    raise RuntimeError("Unable to sample Pride colors with sufficient hue spacing")


scheme_pride = [generate_pride_scheme() for _ in range(10)]

# Berlin / techno club palette: each scheme uses at most one chromatic hue plus
# white (repeats of that hue or white in fg / bg / bg_contrast) — see
# `test_scheme_berlin_is_monochromatic`. Length matches `scheme_pride` so the
# director can rotate between themes without changing scheme-index math.
scheme_berlin = [
    ColorScheme(Color("white"), Color("red"), Color("red")),
    ColorScheme(Color("red"), Color("red"), Color("red")),
    ColorScheme(Color("white"), Color("blue"), Color("blue")),
    ColorScheme(Color("blue"), Color("blue"), Color("blue")),
    ColorScheme(Color("white"), Color("purple"), Color("purple")),
    ColorScheme(Color("purple"), Color("purple"), Color("purple")),
    ColorScheme(Color("white"), Color("magenta"), Color("magenta")),
    ColorScheme(Color("magenta"), Color("magenta"), Color("magenta")),
    ColorScheme(Color("white"), Color("white"), Color("red")),
    ColorScheme(Color("purple"), Color("white"), Color("purple")),
]

scheme_halloween = [
    ColorScheme(Color("purple"), Color("purple"), Color("green")),
    ColorScheme(Color("white"), Color("red"), Color("purple")),
    ColorScheme(Color("green"), Color("blue"), Color("purple")),
    ColorScheme(Color("purple"), Color("blue"), Color("green")),
    ColorScheme(Color("white"), Color("red"), Color("red")),
    ColorScheme(Color("white"), Color("purple"), Color("blue")),
]


color_schemes = scheme_standard
