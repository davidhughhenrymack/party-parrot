from __future__ import annotations

from parrot.patch_bay import get_manual_group, has_manual_dimmer, venue_patches, venues
from parrot.state import State


def get_runtime_fixtures(state: State):
    if state.runtime_patch is not None:
        return state.runtime_patch
    return venue_patches[state.venue]


def get_runtime_manual_group(state: State):
    if state.runtime_manual_group is not None:
        return state.runtime_manual_group
    return get_manual_group(state.venue)


def runtime_has_manual_dimmer(state: State) -> bool:
    if state.manual_dimmer_supported_override is not None:
        return state.manual_dimmer_supported_override
    return has_manual_dimmer(state.venue)


def get_runtime_venues(state: State):
    if state.available_venues:
        return state.available_venues
    return list(venues)
