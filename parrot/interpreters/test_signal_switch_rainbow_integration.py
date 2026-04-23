"""Integration tests for rainbow carrier vs ``ColorBg`` / ``AnyColor`` ordering.

``Combo`` runs children in order. ``ColorRainbow`` runs inside ``SignalSwitch``. If a
solid color interpreter (``ColorBg``, ``AnyColor``, ``for_bulbs(AnyColor)``) runs
*after* ``SignalSwitch``, it overwrites per-fixture rainbow hues every frame.

Chill / rave / stroby rigs were updated so solid color runs first, then
``SignalSwitch``, so the rainbow carrier is visible while held.
"""

from __future__ import annotations

import pytest

from parrot.director.color_scheme import ColorScheme
from parrot.director.frame import Frame, FrameSignal
from parrot.fixtures.led_par import ParRGB
from parrot.interpreters.base import ColorBg, InterpreterArgs
from parrot.interpreters.combo import combo
from parrot.interpreters.dimmer import GentlePulse
from parrot.interpreters.signal import signal_switch
from parrot.utils.colour import Color


def _quiet_frame(*, rainbow: float) -> Frame:
    values = {signal: 0.0 for signal in FrameSignal}
    values[FrameSignal.rainbow] = rainbow
    return Frame(values)


def _rgb_tuple(c: Color) -> tuple[float, float, float]:
    return (round(float(c.red), 4), round(float(c.green), 4), round(float(c.blue), 4))


@pytest.fixture
def scheme() -> ColorScheme:
    return ColorScheme(
        Color("#ff0000"),
        Color("#0033cc"),
        Color("#aaaaaa"),
        allows_rainbow=True,
    )


@pytest.fixture
def args() -> InterpreterArgs:
    return InterpreterArgs(allow_rainbows=True)


def test_chill_par_combo_color_bg_then_signal_switch_shows_rainbow_hues(
    scheme: ColorScheme, args: InterpreterArgs
):
    """Matches fixed chill ``Par``: ``combo(ColorBg, signal_switch(...))``."""
    pars = [ParRGB(patch=1), ParRGB(patch=20)]
    ComboCls = combo(ColorBg, signal_switch(GentlePulse))
    interp = ComboCls(pars, args)

    interp.interpreters[1].responds_to[FrameSignal.rainbow] = True

    frame = _quiet_frame(rainbow=1.0)
    frame.time = 12.5

    interp.step(frame, scheme)

    rgbs = {_rgb_tuple(p.get_color()) for p in pars}
    assert len(rgbs) >= 2, (
        "rainbow carrier should yield distinct per-fixture hues (ColorRainbow after ColorBg)"
    )


def test_legacy_signal_switch_then_color_bg_collapses_rainbow_to_solid_slot(
    scheme: ColorScheme, args: InterpreterArgs
):
    """Documents the old bug: ``combo(signal_switch(...), ColorBg)`` wipes rainbow."""
    pars = [ParRGB(patch=1), ParRGB(patch=20)]
    ComboCls = combo(signal_switch(GentlePulse), ColorBg)
    interp = ComboCls(pars, args)

    interp.interpreters[0].responds_to[FrameSignal.rainbow] = True

    frame = _quiet_frame(rainbow=1.0)
    frame.time = 12.5

    interp.step(frame, scheme)

    slot = interp.interpreters[1].slot
    expected = _rgb_tuple(getattr(scheme, slot))
    for p in pars:
        assert _rgb_tuple(p.get_color()) == expected
