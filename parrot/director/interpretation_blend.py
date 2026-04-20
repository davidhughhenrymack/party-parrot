from __future__ import annotations

from dataclasses import dataclass

from parrot.fixtures.base import FixtureBase
from parrot.interpreters.base import InterpreterBase


@dataclass
class InterpretationBlend:
    """Tracks parallel outgoing (primary) + incoming fixture copies + lerp output."""

    start_time: float
    bucket_indices: frozenset[int]
    incoming_interpreters: dict[int, InterpreterBase]
    incoming_fixtures: dict[int, list[FixtureBase]]
    lerp_fixtures: dict[int, list[FixtureBase]]
