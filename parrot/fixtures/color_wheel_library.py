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


# --- Chauvet Rogue R2 Beam (18CH ch 9) — Rogue R2 Beam User Manual Rev. 2.
# DMX midpoints land in each 4-wide slot (000–004 Open, 005–008 Red, …).
_CHAUVET_ROGUE_BEAM_R2X_WHEEL: list[ColorWheelSlotRow] = [
    {"dmx_value": 2, "color": "white", "label": "Open"},
    {"dmx_value": 6, "color": "red", "label": "Red (1)"},
    {"dmx_value": 10, "color": "#FFC900", "label": "Deep yellow (2)"},
    {"dmx_value": 14, "color": "turquoise", "label": "Turquoise (3)"},
    {"dmx_value": 18, "color": "green", "label": "Green (4)"},
    {"dmx_value": 22, "color": "lightgreen", "label": "Light green (5)"},
    {"dmx_value": 26, "color": "#D8B4F0", "label": "Light purple (6)"},
    {"dmx_value": 30, "color": "pink", "label": "Pink (7)"},
    {"dmx_value": 34, "color": "#FFFF99", "label": "Light yellow (8)"},
    {"dmx_value": 38, "color": "magenta", "label": "Magenta (9)"},
    {"dmx_value": 42, "color": "blue", "label": "Blue (10)"},
    {"dmx_value": 46, "color": "#FFB46B", "label": "CTO 3200 K (11)"},
    {"dmx_value": 50, "color": "#FFEEDD", "label": "CTO 5600 K (12)"},
    {"dmx_value": 54, "color": "#F0F8FF", "label": "CTO 6500 K (13)"},
    {"dmx_value": 58, "color": "#4B0082", "label": "UV (14)"},
]

# --- Chauvet Rogue™ RH1 Hybrid (20CH ch 8 / 25CH ch 9) — Rogue RH1 Hybrid
# User Manual Rev. 4, page 27 (20CH) / page 22 (25CH). The same color wheel
# is used in both personalities; DMX midpoints land in each 4-wide slot:
# 000–003 Open, 004–007 Red, 008–011 Orange, 012–015 Cyan, …, 052–059 UV.
_CHAUVET_ROGUE_HYBRID_RH1_WHEEL: list[ColorWheelSlotRow] = [
    {"dmx_value": 2, "color": "white", "label": "Open"},
    {"dmx_value": 6, "color": "red", "label": "Red (1)"},
    {"dmx_value": 10, "color": "#FF6A00", "label": "Orange (2)"},
    {"dmx_value": 14, "color": "cyan", "label": "Cyan (3)"},
    {"dmx_value": 18, "color": "lightgreen", "label": "Light green (4)"},
    {"dmx_value": 22, "color": "#FFFF99", "label": "Light yellow (5)"},
    {"dmx_value": 26, "color": "green", "label": "Green (6)"},
    {"dmx_value": 30, "color": "magenta", "label": "Magenta (7)"},
    {"dmx_value": 34, "color": "#001A66", "label": "Dark blue (8)"},
    {"dmx_value": 38, "color": "#B58A00", "label": "Dark yellow (9)"},
    {"dmx_value": 42, "color": "blue", "label": "Blue (10)"},
    {"dmx_value": 46, "color": "#FFEEDD", "label": "CTO 5600 K (11)"},
    {"dmx_value": 50, "color": "#F0F8FF", "label": "CTO 6500 K (12)"},
    {"dmx_value": 56, "color": "#4B0082", "label": "UV (13)"},
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
