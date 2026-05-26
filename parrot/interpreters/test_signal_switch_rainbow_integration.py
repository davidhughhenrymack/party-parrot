"""Integration tests for rainbow carrier and color interpreter ordering.

``Combo`` runs children in order, so these checks make sure rainbow-capable
color interpreters leave per-fixture hues visible even when composed before or
after a signal-switch rainbow carrier.
"""

from __future__ import annotations

import pytest

from parrot.director.color_scheme import ColorScheme
from parrot.director.frame import Frame, FrameSignal
from parrot.fixtures.led_par import ParRGB
from parrot.fixtures.motionstrip import Motionstrip38
from parrot.interpreters.base import ColorBg, InterpreterArgs
from parrot.interpreters.combo import combo
from parrot.interpreters.dimmer import GentlePulse
from parrot.interpreters.signal import signal_switch
from parrot.utils.colour import Color


def _quiet_frame(*, rainbow: float) -> Frame:
    values = {signal: 0.0 for signal in FrameSignal}
    values[FrameSignal.rainbow] = rainbow
    return Frame(values)


def _carrier_frame(signal: FrameSignal, value: float) -> Frame:
    values = {s: 0.0 for s in FrameSignal}
    values[signal] = value
    return Frame(values)


def _rgb_tuple(c: Color) -> tuple[float, float, float]:
    return (round(float(c.red), 4), round(float(c.green), 4), round(float(c.blue), 4))


@pytest.fixture
def scheme() -> ColorScheme:
    return ColorScheme(
        Color("#ff0000"),
        Color("#0033cc"),
        Color("#aaaaaa"),
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


def test_signal_switch_then_color_bg_still_shows_rainbow_hues(
    scheme: ColorScheme, args: InterpreterArgs
):
    pars = [ParRGB(patch=1), ParRGB(patch=20)]
    ComboCls = combo(signal_switch(GentlePulse), ColorBg)
    interp = ComboCls(pars, args)

    interp.interpreters[0].responds_to[FrameSignal.rainbow] = True

    frame = _quiet_frame(rainbow=1.0)
    frame.time = 12.5

    interp.step(frame, scheme)

    rgbs = {_rgb_tuple(p.get_color()) for p in pars}
    assert len(rgbs) >= 2


def test_signal_switch_exit_clears_strobe_on_parent_and_bulbs(
    scheme: ColorScheme, args: InterpreterArgs
):
    fixture = Motionstrip38(1)
    SignalSwitchCls = signal_switch(GentlePulse)
    interp = SignalSwitchCls([fixture], args)
    interp.responds_to[FrameSignal.strobe] = True

    interp.step(_carrier_frame(FrameSignal.strobe, 1.0), scheme)
    assert fixture.get_strobe() == 220
    assert all(bulb.get_strobe() == 220 for bulb in fixture.get_bulbs())

    interp.exit(_carrier_frame(FrameSignal.strobe, 0.0), scheme)

    assert fixture.get_strobe() == 0
    assert all(bulb.get_strobe() == 0 for bulb in fixture.get_bulbs())
