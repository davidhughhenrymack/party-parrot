from parrot.director.color_scheme import ColorScheme
from parrot.director.frame import Frame, FrameSignal
from parrot.fixtures.led_par import ParRGB
from parrot.interpreters.base import InterpreterArgs
from parrot.interpreters.strobe import (
    StrobeChannelSustained,
    StrobeHighSustained,
    StrobeOff,
    StrobeOn,
)
from parrot.utils.colour import Color


def _frame() -> Frame:
    return Frame({signal: 0.0 for signal in FrameSignal})


def _scheme() -> ColorScheme:
    return ColorScheme(Color("red"), Color("blue"), Color("green"))


def test_strobe_off_clears_existing_strobe_value() -> None:
    fixture = ParRGB(1)
    fixture.set_strobe(200)

    StrobeOff([fixture], InterpreterArgs(True)).step(_frame(), _scheme())

    assert fixture.get_strobe() == 0
    assert fixture.values[4] == 0


def test_strobe_on_exit_clears_existing_strobe_value() -> None:
    fixture = ParRGB(1)
    interpreter = StrobeOn([fixture], InterpreterArgs(True), strobe_value=200)
    interpreter.step(_frame(), _scheme())

    interpreter.exit(_frame(), _scheme())

    assert fixture.get_strobe() == 0
    assert fixture.values[4] == 0


def test_strobe_high_sustained_exit_clears_strobe_and_dimmer() -> None:
    fixture = ParRGB(1)
    interpreter = StrobeHighSustained([fixture], InterpreterArgs(True), strobe_value=200)
    interpreter.step(_frame(), _scheme())

    interpreter.exit(_frame(), _scheme())

    assert fixture.get_strobe() == 0
    assert fixture.values[4] == 0
    assert fixture.get_dimmer() == 0


def test_strobe_channel_sustained_exit_clears_existing_strobe_value() -> None:
    fixture = ParRGB(1)
    interpreter = StrobeChannelSustained([fixture], InterpreterArgs(True), strobe_value=200)
    interpreter.step(_frame(), _scheme())

    interpreter.exit(_frame(), _scheme())

    assert fixture.get_strobe() == 0
    assert fixture.values[4] == 0
