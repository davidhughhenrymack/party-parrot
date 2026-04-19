from collections import namedtuple
import math
import random
from typing import Generic, Literal, TypeVar
from beartype import beartype
from parrot.director.frame import Frame, FrameSignal
from parrot.fixtures.base import FixtureBase
from parrot.director.color_scheme import ColorScheme
from parrot.utils.colour import Color
from colorama import Fore, Style

T = TypeVar("T", bound=FixtureBase)

InterpreterArgs = namedtuple(
    "InterpreterArgs", ["hype", "allow_rainbows", "min_hype", "max_hype"]
)


@beartype
def acceptable_test(args: InterpreterArgs, hype, has_rainbow):
    if has_rainbow and not args.allow_rainbows:
        return False

    if hype < args.min_hype or hype > args.max_hype:
        return False

    return True


@beartype
class InterpreterBase(Generic[T]):
    has_rainbow = False
    hype = 0

    def __init__(self, group: list[T], args: InterpreterArgs):
        self.group = group
        self.interpreter_args = args

    def step(self, frame: Frame, scheme: ColorScheme):
        pass

    def exit(self, frame: Frame, scheme: ColorScheme):
        pass

    def get_hype(self):
        return self.__class__.hype

    @classmethod
    def acceptable(cls, args: InterpreterArgs) -> bool:
        return acceptable_test(args, cls.hype, cls.has_rainbow)

    def __str__(self) -> str:
        return f"{Fore.YELLOW}{self.__class__.__name__}{Style.RESET_ALL}"


@beartype
def with_args(name, interpreter, new_hype=None, new_has_rainbow=None, **kwargs):

    class WithArgs(InterpreterBase):
        def __init__(self, group, args):
            super().__init__(group, args)
            self.interpreter = interpreter(group, args, **kwargs)
            self.name = name

        @classmethod
        def acceptable(cls, args):
            if new_hype is not None and new_has_rainbow is not None:
                return acceptable_test(args, new_hype, new_has_rainbow)
            return interpreter.acceptable(args)

        def step(self, frame, scheme):
            self.interpreter.step(frame, scheme)

        def exit(self, frame, scheme):
            self.interpreter.exit(frame, scheme)

        def get_hype(self):
            return new_hype if new_hype is not None else self.interpreter.get_hype()

        def __str__(self):
            n = str(self.interpreter) if self.name is None else self.name
            return f"{n}"

    return WithArgs


@beartype
class Noop(InterpreterBase):
    def step(self, frame, scheme):
        pass


@beartype
class ColorFg(InterpreterBase):
    hype = 30

    def __str__(self):
        return f"🎨{Fore.MAGENTA}Fg{Style.RESET_ALL}"

    def step(self, frame, scheme):
        for i in self.group:
            i.set_color(scheme.fg)


@beartype
class ColorAlternateBg(InterpreterBase):
    def __str__(self):
        return f"🔄{Fore.MAGENTA}AlternateBg{Style.RESET_ALL}"

    def step(self, frame, scheme):
        for idx, fixture in enumerate(self.group):
            fixture.set_color(scheme.bg if idx % 2 == 0 else scheme.bg_contrast)


@beartype
class ColorBg(InterpreterBase):
    def __str__(self):
        return f"🎨{Fore.MAGENTA}Bg{Style.RESET_ALL}"

    def step(self, frame, scheme):
        for idx, fixture in enumerate(self.group):
            fixture.set_color(scheme.bg)


@beartype
class AnyColor(InterpreterBase):
    """Per-fixture solid slot (``fg`` / ``bg`` / ``bg_contrast``) or all-rainbow.

    At construction, each fixture is assigned a solid color slot chosen uniformly
    from ``fg``, ``bg``, and ``bg_contrast``. Independently, with probability
    ``p_rainbow_all`` the whole group is assigned to cycling rainbow; on the
    first :meth:`step`, that applies only when :attr:`ColorScheme.allows_rainbow`
    and interpreter args allow rainbows (otherwise the per-fixture solid slots
    are used). Rainbow output is delegated to :class:`ColorRainbow`.
    """

    hype = 35

    _SOLID_SLOTS: tuple[str, str, str] = ("fg", "bg", "bg_contrast")

    def __init__(
        self,
        group,
        args,
        color_speed: float = 0.08,
        color_phase_spread: float = 0.2,
        p_rainbow_all: float = 0.2,
    ):
        super().__init__(group, args)
        self._rainbow = ColorRainbow(group, args, color_speed, color_phase_spread)
        self.p_rainbow_all = p_rainbow_all
        self._wants_all_rainbow = random.random() < p_rainbow_all
        self._fixture_slots = [
            random.choice(self._SOLID_SLOTS) for _ in group
        ]
        self._mode: Literal["unset", "rainbow", "solid"] = "unset"

    def __str__(self):
        return f"🎨{Fore.MAGENTA}AnyColor{Style.RESET_ALL}"

    def step(self, frame: Frame, scheme: ColorScheme) -> None:
        if self._mode == "unset":
            if (
                self._wants_all_rainbow
                and scheme.allows_rainbow
                and self.interpreter_args.allow_rainbows
            ):
                self._mode = "rainbow"
            else:
                self._mode = "solid"
        if self._mode == "rainbow":
            self._rainbow.step(frame, scheme)
            return
        for fixture, slot in zip(self.group, self._fixture_slots, strict=True):
            if slot == "fg":
                color = scheme.fg
            elif slot == "bg":
                color = scheme.bg
            else:
                color = scheme.bg_contrast
            fixture.set_color(color)

    def exit(self, frame: Frame, scheme: ColorScheme) -> None:
        self._rainbow.exit(frame, scheme)


@beartype
class ColorRainbow(InterpreterBase):
    has_rainbow = True
    hype = 40

    def __str__(self):
        return f"🌈{Fore.MAGENTA}Rainbow{Style.RESET_ALL}"

    def __init__(self, group, args, color_speed=0.08, color_phase_spread=0.2):
        super().__init__(group, args)
        self.color_speed = color_speed
        self.color_phase_spread = color_phase_spread

    def step(self, frame, scheme):
        for idx, fixture in enumerate(self.group):
            color = Color("red")
            phase = (
                frame.time * self.color_speed
                + self.color_phase_spread / len(self.group) * idx
            )
            color.set_hue(phase - math.floor(phase))
            fixture.set_color(color)


@beartype
class FlashBeat(InterpreterBase):
    hype = 70

    def __str__(self):
        return f"⚡{Fore.MAGENTA}FlashBeat{Style.RESET_ALL}"

    def __init__(self, group, args):
        super().__init__(group, args)
        self.signal = FrameSignal.freq_high

    def step(self, frame, scheme):
        for i in self.group:
            if frame[FrameSignal.sustained_low] > 0.7:
                i.set_dimmer(100)
                i.set_strobe(200)
            elif frame[self.signal] > 0.4:
                i.set_dimmer(frame[self.signal] * 255)
                i.set_strobe(0)
            else:
                i.set_dimmer(0)
                i.set_strobe(0)
