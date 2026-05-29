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
from parrot.director.mode import Mode, mode_key
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
from parrot.interpreters.combo import combo
from parrot.interpreters.randomize import randomize, weighted_randomize
from parrot.interpreters.signal import signal_switch
from parrot.director.animation_registry import REGISTRY, build_interpreter_factory
from parrot_cloud.domain import VenueAnimationAssignmentSpec, VenueSnapshot


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


def _legacy_get_interpreter(
    phrase: Mode,
    fixture_group: List[FixtureBase],
    args: InterpreterArgs,
) -> InterpreterBase:
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


def mode_uses_group_matchers(phrase: Mode) -> bool:
    """Modes whose DSL uses ``Group(...)`` keys must receive the whole patch flat."""
    return _mapping_has_group_matcher(_mode_mapping(phrase))


def _fixture_type_matches(scope_type: str | None, fixture: FixtureBase) -> bool:
    if scope_type is None:
        return True
    if scope_type == "par":
        return isinstance(fixture, Par)
    if scope_type == "moving_head":
        return isinstance(fixture, MovingHead)
    return getattr(fixture, "cloud_fixture_type", None) == scope_type


def _assignment_matches(
    assignment: VenueAnimationAssignmentSpec,
    fixture: FixtureBase,
    group_index: int,
) -> bool:
    if assignment.fixture_group_name is not None:
        if (
            _fixture_cloud_group_casefold(fixture)
            != assignment.fixture_group_name.casefold()
        ):
            return False
    if assignment.fixture_index_filter == "odds" and group_index % 2 != 1:
        return False
    if assignment.fixture_index_filter == "evens" and group_index % 2 != 0:
        return False
    return _fixture_type_matches(assignment.fixture_type, fixture)


def _assignment_sort_key(
    assignment: VenueAnimationAssignmentSpec,
) -> tuple[int, str, str, str, int]:
    specificity = (
        (0 if assignment.fixture_group_name is not None else 4)
        + (0 if assignment.fixture_type is not None else 2)
        + (0 if assignment.fixture_index_filter is not None else 1)
    )
    return (
        specificity,
        assignment.fixture_group_name or "",
        assignment.fixture_type or "",
        assignment.fixture_index_filter or "",
        assignment.order_index,
    )


def _assignments_for_mode(
    phrase: Mode | str,
    venue_snapshot: VenueSnapshot | None,
) -> list[VenueAnimationAssignmentSpec]:
    if venue_snapshot is None:
        return []
    key = mode_key(phrase)
    return [
        assignment
        for assignment in venue_snapshot.animation_assignments
        if assignment.lighting_mode_key == key
    ]


def _uses_legacy_reference(assignments: list[VenueAnimationAssignmentSpec]) -> bool:
    return any(
        assignment.animation_spec.get("type") == "legacy_mode"
        for assignment in assignments
    )


def _group_assignments_by_scope(
    assignments: list[VenueAnimationAssignmentSpec],
) -> list[tuple[VenueAnimationAssignmentSpec, list[VenueAnimationAssignmentSpec]]]:
    grouped: dict[
        tuple[str | None, str | None, str | None],
        list[VenueAnimationAssignmentSpec],
    ] = {}
    for assignment in sorted(assignments, key=_assignment_sort_key):
        key = (
            assignment.fixture_group_name,
            assignment.fixture_type,
            assignment.fixture_index_filter,
        )
        grouped.setdefault(key, []).append(assignment)
    out = []
    for rows in grouped.values():
        out.append((rows[0], sorted(rows, key=lambda item: item.order_index)))
    return sorted(out, key=lambda item: _assignment_sort_key(item[0]))


def _animation_category(spec: dict) -> str:
    expression_type = str(spec.get("type", "animation"))
    if expression_type in {"animation", "with_args"}:
        return REGISTRY[str(spec["key"])].category
    if expression_type == "signal_switch":
        return _animation_category(dict(spec["animation"]))
    if expression_type == "for_bulbs":
        children = [dict(child) for child in spec.get("children", [])]
        child_categories = {_animation_category(child) for child in children}
        return child_categories.pop() if len(child_categories) == 1 else "Stack"
    if expression_type in {"randomize", "combo"}:
        children = [
            dict(child) for child in spec.get("options", spec.get("children", []))
        ]
        child_categories = {_animation_category(child) for child in children}
        return child_categories.pop() if len(child_categories) == 1 else "Stack"
    if expression_type == "weighted_randomize":
        children = [dict(item)["animation"] for item in spec.get("options", [])]
        child_categories = {_animation_category(dict(child)) for child in children}
        return child_categories.pop() if len(child_categories) == 1 else "Stack"
    return "Stack"


def _weight_percent(spec: dict) -> int | None:
    raw = spec.get("weight_percent")
    if raw is None:
        return None
    try:
        value = int(raw)
    except (TypeError, ValueError):
        return None
    return max(0, value)


def _assignment_animation_options(
    assignment: VenueAnimationAssignmentSpec,
) -> list[tuple[str, int | None, dict]]:
    spec = dict(assignment.animation_spec)
    weight = _weight_percent(spec)
    expression_type = str(spec.get("type", "animation"))
    if expression_type == "combo":
        return [
            (_animation_category(dict(child)), weight, dict(child))
            for child in spec.get("children", [])
        ]
    if expression_type == "randomize":
        return [
            (_animation_category(dict(child)), weight, dict(child))
            for child in spec.get("options", [])
        ]
    if expression_type == "weighted_randomize":
        out = []
        for item in spec.get("options", []):
            row = dict(item)
            child = dict(row["animation"])
            out.append((_animation_category(child), int(row["weight"]), child))
        return out
    return [(_animation_category(spec), weight, spec)]


def _build_category_combo(
    assignments: list[VenueAnimationAssignmentSpec],
) -> type[InterpreterBase]:
    options_by_category: dict[str, list[tuple[int | None, type[InterpreterBase]]]] = {}
    for assignment in assignments:
        for category, weight, spec in _assignment_animation_options(assignment):
            options_by_category.setdefault(category, []).append(
                (weight, build_interpreter_factory(spec))
            )

    children: list[type[InterpreterBase]] = []
    for category in sorted(options_by_category):
        options = options_by_category[category]
        if len(options) == 1:
            children.append(options[0][1])
            continue
        if any(weight is not None for weight, _factory in options):
            explicit_total = sum(
                weight for weight, _factory in options if weight is not None
            )
            unset_count = sum(1 for weight, _factory in options if weight is None)
            unset_weight = (
                max(0, 100 - explicit_total) / unset_count if unset_count > 0 else 0
            )
            weighted_options = [
                (weight if weight is not None else unset_weight, factory)
                for weight, factory in options
            ]
            children.append(weighted_randomize(*weighted_options))
        else:
            children.append(randomize(*(factory for _weight, factory in options)))
    if not children:
        return Dimmer0
    if len(children) == 1:
        return children[0]
    return combo(*children)


def get_interpreter(
    phrase: Mode | str,
    fixture_group: List[FixtureBase],
    args: InterpreterArgs,
    venue_snapshot: VenueSnapshot | None = None,
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
    key = mode_key(phrase)
    fixed_mode_keys = {"blackout", "test", "home"}
    if venue_snapshot is None:
        if not isinstance(phrase, Mode):
            return Dimmer0(fixture_group, args)
        return _legacy_get_interpreter(phrase, fixture_group, args)
    assignments = _assignments_for_mode(phrase, venue_snapshot)
    if key in fixed_mode_keys or _uses_legacy_reference(assignments):
        legacy_mode = Mode[key] if key in Mode.__members__ else None
        if legacy_mode is None:
            return Dimmer0(fixture_group, args)
        return _legacy_get_interpreter(legacy_mode, fixture_group, args)

    if not fixture_group:
        return Dimmer0(fixture_group, args)
    if not assignments:
        return Dimmer0(fixture_group, args)

    items = _group_assignments_by_scope(assignments)
    children: list[InterpreterBase] = []
    remaining = list(fixture_group)
    group_index_by_fixture_id = {
        id(fixture): idx for idx, fixture in enumerate(fixture_group)
    }
    for representative, scoped_assignments in items:
        matched = [
            f
            for f in remaining
            if _assignment_matches(
                representative,
                f,
                group_index_by_fixture_id[id(f)],
            )
        ]
        if not matched:
            continue
        matched_ids = {id(f) for f in matched}
        remaining = [f for f in remaining if id(f) not in matched_ids]
        group_factory = signal_switch(_build_category_combo(scoped_assignments))
        children.append(group_factory(matched, args))
    if remaining:
        children.append(Dimmer0(remaining, args))
    if not children:
        return Dimmer0(fixture_group, args)
    if len(children) == 1:
        return children[0]
    return CompositeInterpreter(fixture_group, args, children)
