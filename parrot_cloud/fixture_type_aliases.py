"""Maps deprecated ``fixture_type`` strings from older DB rows to current catalog keys."""

from __future__ import annotations

from beartype import beartype

_LEGACY_TO_CANONICAL_FIXTURE_TYPE: dict[str, str] = {
    "chauvet_rogue_beam_r2": "chauvet_rogue_beam_r2x",
    "chauvet_intimidator_hybrid_140sr": "chauvet_rogue_hybrid_rh1",
    "chauvet_intimidator_hybrid_140sr_13ch": "chauvet_rogue_hybrid_rh1_13ch",
}


@beartype
def normalize_fixture_type_key(fixture_type: str) -> str:
    """Resolve deprecated fixture-type strings so venues and specs stay loadable."""
    return _LEGACY_TO_CANONICAL_FIXTURE_TYPE.get(fixture_type, fixture_type)
