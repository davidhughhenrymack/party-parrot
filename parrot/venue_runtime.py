from __future__ import annotations

from beartype import beartype

from parrot.fixtures.base import FixtureBase, FixtureGroup
from parrot.patch_bay import get_manual_group, venue_patches, venues
from parrot.state import State


@beartype
def replace_fixture_leaf_in_runtime_patch(
    patch: list[FixtureBase],
    old_leaf: FixtureBase,
    new_leaf: FixtureBase,
) -> bool:
    """Replace ``old_leaf`` with ``new_leaf`` in a runtime patch tree (in-place)."""
    for idx, entry in enumerate(patch):
        if isinstance(entry, FixtureGroup):
            for j, f in enumerate(entry.fixtures):
                if f is old_leaf:
                    entry.fixtures[j] = new_leaf
                    return True
        elif entry is old_leaf:
            patch[idx] = new_leaf
            return True
    return False


def get_runtime_fixtures(state: State):
    if state.runtime_patch is not None:
        return state.runtime_patch
    return venue_patches[state.venue]


def get_runtime_manual_group(state: State):
    if state.runtime_manual_group is not None:
        return state.runtime_manual_group
    return get_manual_group(state.venue)


def get_runtime_venues(state: State):
    if state.available_venues:
        return state.available_venues
    return list(venues)
