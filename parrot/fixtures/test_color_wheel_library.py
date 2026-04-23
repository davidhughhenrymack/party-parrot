"""Color wheel library stays aligned with mover fixtures and catalog keys."""

from __future__ import annotations

from parrot.fixtures.chauvet.rogue_hybrid_rh1 import COLOR_WHEEL as HYBRID_WHEEL
from parrot.fixtures.chauvet.rogue_beam_r2 import COLOR_WHEEL as ROGUE_WHEEL
from parrot.fixtures.color_wheel_library import (
    COLOR_WHEEL_LIBRARY,
    color_wheel_entries_for_fixture_type,
    color_wheel_slots_for_api,
)
from parrot.utils.colour import Color


def test_library_matches_fixture_module_lists() -> None:
    assert len(ROGUE_WHEEL) == len(COLOR_WHEEL_LIBRARY["chauvet_rogue_beam_r2x"])
    assert len(HYBRID_WHEEL) == len(COLOR_WHEEL_LIBRARY["chauvet_rogue_hybrid_rh1"])
    for i, entry in enumerate(ROGUE_WHEEL):
        lib = COLOR_WHEEL_LIBRARY["chauvet_rogue_beam_r2x"][i]
        assert entry.dmx_value == lib["dmx_value"]
        assert entry.color.hex_l == Color(str(lib["color"])).hex_l
    for i, entry in enumerate(HYBRID_WHEEL):
        lib = COLOR_WHEEL_LIBRARY["chauvet_rogue_hybrid_rh1"][i]
        assert entry.dmx_value == lib["dmx_value"]
        assert entry.color.hex_l == Color(str(lib["color"])).hex_l


def test_color_wheel_entries_for_fixture_type_unknown() -> None:
    assert color_wheel_entries_for_fixture_type("par_rgb") == []


def test_legacy_catalog_keys_resolve_color_wheel_alias() -> None:
    slots = color_wheel_slots_for_api("chauvet_rogue_beam_r2")
    assert slots is not None
    assert slots[0]["dmx_value"] == 2


def test_api_slots_include_rgb_and_optional_label() -> None:
    slots = color_wheel_slots_for_api("chauvet_rogue_hybrid_rh1")
    assert slots is not None
    sky = next(s for s in slots if s.get("label") == "Sky Blue")
    assert sky["dmx_value"] == 18
    assert len(sky["rgb"]) == 3
