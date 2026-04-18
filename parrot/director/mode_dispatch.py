"""DSL machinery for ``mode_interpretations``.

This module owns the matchers (``Group``, class, tuple), how they are ordered,
and how a ``Mode`` + a patch of fixtures turns into a concrete
``InterpreterBase``. Kept separate so ``mode_interpretations.py`` can read as a
pure expression of matches-to-interpreters.
"""

from __future__ import annotations

from typing import Dict, List, Tuple, Type, Union

from beartype import beartype

from parrot.director.color_scheme import ColorScheme
from parrot.director.frame import Frame
from parrot.director.mode import Mode
from parrot.fixtures.base import FixtureBase
from parrot.fixtures.chauvet.colorband_pix import ChauvetColorBandPiX_36Ch
from parrot.fixtures.chauvet.derby import ChauvetDerby
from parrot.fixtures.chauvet.rotosphere import ChauvetRotosphere_28Ch
from parrot.fixtures.laser import Laser
from parrot.fixtures.led_par import Par
from parrot.fixtures.mirrorball import Mirrorball
from parrot.fixtures.motionstrip import Motionstrip
from parrot.fixtures.moving_head import MovingHead
from parrot.interpreters.base import InterpreterArgs, InterpreterBase
from parrot.interpreters.dimmer import Dimmer0
from parrot.interpreters.randomize import randomize


@beartype
def _fixture_cloud_group_casefold(fixture: FixtureBase) -> str | None:
    raw = getattr(fixture, "cloud_group_name", None)
    if raw is None or not isinstance(raw, str):
        return None
    s = raw.strip()
    return s.casefold() if s else None


class Group:
    """DSL matcher for fixtures by their cloud group name (case-insensitive, trimmed)."""

    def __init__(self, name: str):
        self.name = name
        self._key = name.strip().casefold()

    def matches(self, fixture: FixtureBase) -> bool:
        return _fixture_cloud_group_casefold(fixture) == self._key

    def __hash__(self) -> int:
        return hash(("Group", self._key))

    def __eq__(self, other: object) -> bool:
        return isinstance(other, Group) and other._key == self._key

    def __repr__(self) -> str:
        return f"Group({self.name!r})"


Matcher = Union[Type[FixtureBase], Group, Tuple["Matcher", ...]]


def _matcher_matches(matcher: Matcher, fixture: FixtureBase) -> bool:
    if isinstance(matcher, Group):
        return matcher.matches(fixture)
    if isinstance(matcher, tuple):
        return all(_matcher_matches(m, fixture) for m in matcher)
    return isinstance(fixture, matcher)


def _mapping_has_group_matcher(mapping: dict) -> bool:
    def contains_group(key: object) -> bool:
        if isinstance(key, Group):
            return True
        if isinstance(key, tuple):
            return any(contains_group(k) for k in key)
        return False

    return any(contains_group(k) for k in mapping)


@beartype
class CompositeInterpreter(InterpreterBase[FixtureBase]):
    """Runs child interpreters in order; used when a mode partitions a flat fixture list."""

    def __init__(
        self,
        group: list[FixtureBase],
        args: InterpreterArgs,
        children: list[InterpreterBase],
    ):
        super().__init__(group, args)
        self._children = children

    @property
    def children(self) -> list[InterpreterBase]:
        """Child interpreters, each bound to its own partitioned sub-group.

        Exposed so tree-printers can render one row per child (with the child's
        own ``group``) instead of collapsing the whole composite onto a single
        line with the parent's flat group.
        """
        return list(self._children)

    def step(self, frame: Frame, scheme: ColorScheme) -> None:
        for c in self._children:
            c.step(frame, scheme)

    def exit(self, frame: Frame, scheme: ColorScheme) -> None:
        for c in self._children:
            c.exit(frame, scheme)

    def __str__(self) -> str:
        return " | ".join(str(c) for c in self._children)


# Subclasses match before their parents: Mirrorball is a Par subclass.
_INTERPRETER_TYPE_ORDER: Tuple[Type[FixtureBase], ...] = (
    Mirrorball,
    MovingHead,
    Motionstrip,
    ChauvetColorBandPiX_36Ch,
    Laser,
    ChauvetRotosphere_28Ch,
    ChauvetDerby,
    Par,
)


def _sorted_items(
    mapping: Dict[Matcher, List[InterpreterBase]],
) -> List[Tuple[Matcher, List[InterpreterBase]]]:
    rank = {cls: i for i, cls in enumerate(_INTERPRETER_TYPE_ORDER)}

    def sort_key(item: Tuple[Matcher, List[InterpreterBase]]) -> Tuple[int, int, str]:
        k = item[0]
        # Most specific first: (Group + class) > bare Group > bare class (subclass-aware).
        if isinstance(k, tuple):
            cls = next((m for m in k if isinstance(m, type)), None)
            return (0, rank.get(cls, 1000) if cls else 0, repr(k))
        if isinstance(k, Group):
            return (1, 0, k.name)
        return (2, rank.get(k, 1000), k.__name__)

    return sorted(mapping.items(), key=sort_key)


def _mode_mapping(phrase: Mode) -> Dict[Matcher, List[InterpreterBase]]:
    from parrot.director.mode_interpretations import mode_interpretations

    return mode_interpretations.get(phrase, {})


def mode_uses_group_matchers(phrase: Mode) -> bool:
    """Modes whose DSL uses ``Group(...)`` keys must receive the whole patch flat."""
    return _mapping_has_group_matcher(_mode_mapping(phrase))


def get_interpreter(
    phrase: Mode,
    fixture_group: List[FixtureBase],
    args: InterpreterArgs,
) -> InterpreterBase:
    """Pick the interpreter(s) for a group of fixtures under ``phrase``.

    Runs the mode DSL against ``fixture_group`` as a partition pass: matchers
    are visited most-specific first (``(Group, Class)`` → bare ``Group`` →
    class, subclass-aware) and each one consumes whichever fixtures still
    remain. Homogeneous inputs collapse to a single interpreter; heterogeneous
    inputs (e.g. a cloud group mixing a mirrorball with moving heads) land on
    :class:`CompositeInterpreter` so each class gets the pack declared for it,
    rather than silently inheriting ``fixture_group[0]``'s interpreter.

    The director calls this once per cloud group, so ``Group(...)`` matchers in
    the DSL effectively re-scope to "the current bucket" — which is why
    unrelated groups (TRACK vs TRUSS MOVERS) end up with independent random
    picks rather than being lumped under one ``MovingHead`` row.
    """
    if not fixture_group:
        return Dimmer0(fixture_group, args)

    mapping = _mode_mapping(phrase)
    items = _sorted_items(mapping)

    children: list[InterpreterBase] = []
    remaining = list(fixture_group)
    for key, options in items:
        matched = [f for f in remaining if _matcher_matches(key, f)]
        if not matched:
            continue
        matched_ids = {id(f) for f in matched}
        remaining = [f for f in remaining if id(f) not in matched_ids]
        children.append(randomize(*options)(matched, args))
    if remaining:
        children.append(Dimmer0(remaining, args))
    if not children:
        return Dimmer0(fixture_group, args)
    if len(children) == 1:
        return children[0]
    return CompositeInterpreter(fixture_group, args, children)
