"""Indexed color-wheel slots keyed by ``parrot_cloud`` fixture type keys.

Single source of truth for DMX snap midpoints and preview RGB for web (fixture-types API)
and desktop (``color_wheel_entries_for_fixture_type``). Keep in sync with fixture manuals.
"""

from __future__ import annotations

from typing import NotRequired, TypedDict

from beartype import beartype

from parrot.fixtures.base import ColorWheelEntry
from parrot.utils.colour import Color


class ColorWheelSlotRow(TypedDict):
    """Serializable row; ``label`` is optional (UI / docs)."""

    dmx_value: int
    color: str
    label: NotRequired[str]


# --- Chauvet Rogue Beam R2 / R2X Beam (19CH ch 9) — Rogue R2X Beam User Manual Rev. 1
_CHAUVET_ROGUE_BEAM_R2X_WHEEL: list[ColorWheelSlotRow] = [
    {"dmx_value": 2, "color": "white", "label": "Open"},
    {"dmx_value": 6, "color": "red", "label": "Color 1"},
    {"dmx_value": 10, "color": "#FF6600", "label": "Color 2"},
    {"dmx_value": 14, "color": "yellow", "label": "Color 3"},
    {"dmx_value": 18, "color": "green", "label": "Color 4"},
    {"dmx_value": 22, "color": "lightgreen", "label": "Color 5"},
    {"dmx_value": 26, "color": "Turquoise", "label": "Color 6"},
    {"dmx_value": 30, "color": "#87ceeb", "label": "Color 7"},
    {"dmx_value": 34, "color": "blue", "label": "Color 8"},
    {"dmx_value": 38, "color": "magenta", "label": "Color 9"},
    {"dmx_value": 42, "color": "Lightpink", "label": "Color 10"},
    {"dmx_value": 46, "color": "pink", "label": "Color 11"},
    {"dmx_value": 50, "color": "#FFA500", "label": "Color 12"},
    {"dmx_value": 54, "color": "#FFE4B5", "label": "Color 13"},
    {"dmx_value": 58, "color": "BlueViolet", "label": "Color 14"},
]

# --- Rogue RH1 Hybrid (Intimidator Hybrid 140SR) Rev. 1 (19CH ch 6 / 13CH ch 3)
_CHAUVET_ROGUE_HYBRID_RH1_WHEEL: list[ColorWheelSlotRow] = [
    {"dmx_value": 2, "color": "white"},
    {"dmx_value": 6, "color": "red"},
    {"dmx_value": 10, "color": "yellow"},
    {"dmx_value": 14, "color": "green"},
    {"dmx_value": 18, "color": "#87ceeb", "label": "Sky Blue"},
    {"dmx_value": 22, "color": "#e6e6fa", "label": "Lavender"},
    {"dmx_value": 26, "color": "#ffff99", "label": "Canary Yellow"},
    {"dmx_value": 31, "color": "blue"},
    {"dmx_value": 36, "color": "magenta"},
    {"dmx_value": 41, "color": "lime", "label": "Lime Green"},
    {"dmx_value": 46, "color": "#fff8f0", "label": "Natural White"},
    {"dmx_value": 51, "color": "#dde8f0", "label": "Cool White"},
    {"dmx_value": 56, "color": "BlueViolet", "label": "Ultraviolet"},
]

# Keys match canonical ``FixtureTypeDefinition.key`` in ``parrot_cloud.fixture_catalog``.
COLOR_WHEEL_LIBRARY: dict[str, list[ColorWheelSlotRow]] = {
    "chauvet_rogue_beam_r2x": _CHAUVET_ROGUE_BEAM_R2X_WHEEL,
    "chauvet_rogue_hybrid_rh1": _CHAUVET_ROGUE_HYBRID_RH1_WHEEL,
}

# Pre-rename catalog keys still appear in older venues / tests.
_LEGACY_COLOR_WHEEL_KEY: dict[str, str] = {
    "chauvet_rogue_beam_r2": "chauvet_rogue_beam_r2x",
    "chauvet_intimidator_hybrid_140sr": "chauvet_rogue_hybrid_rh1",
}


def _canonical_wheel_catalog_key(fixture_type_key: str) -> str:
    return _LEGACY_COLOR_WHEEL_KEY.get(fixture_type_key, fixture_type_key)


@beartype
def color_wheel_entries_for_fixture_type(fixture_type_key: str) -> list[ColorWheelEntry]:
    """Build ``ColorWheelEntry`` rows for mover fixtures (DMX snap + preview)."""
    rows = COLOR_WHEEL_LIBRARY.get(_canonical_wheel_catalog_key(fixture_type_key), ())
    return [
        ColorWheelEntry(Color(str(row["color"])), int(row["dmx_value"])) for row in rows
    ]


@beartype
def color_wheel_slots_for_api(fixture_type_key: str) -> list[dict[str, object]] | None:
    """JSON-serializable slots for web: ``dmx_value``, ``color`` string, ``rgb`` 0–1, optional ``label``."""
    rows = COLOR_WHEEL_LIBRARY.get(_canonical_wheel_catalog_key(fixture_type_key))
    if not rows:
        return None
    out: list[dict[str, object]] = []
    for row in rows:
        c = Color(str(row["color"]))
        slot: dict[str, object] = {
            "dmx_value": int(row["dmx_value"]),
            "color": str(row["color"]),
            "rgb": [float(c.red), float(c.green), float(c.blue)],
        }
        label = row.get("label")
        if label:
            slot["label"] = str(label)
        out.append(slot)
    return out
