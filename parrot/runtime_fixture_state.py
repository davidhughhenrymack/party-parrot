"""
Serialize live fixture output for Party Parrot Cloud (venue editor preview).

Schema version 1 (see parrot_cloud.repository.VenueRepository.set_fixture_runtime_state):
- id: cloud fixture spec id (required)
- dimmer: 0–1 master / fixture dimmer
- rgb: [r,g,b] each 0–1 — aggregate color for simple fixtures
- pan_deg, tilt_deg: moving heads (degrees, fixture logical angles)
- bar_pan_deg: pan for linear bars (matches MotionstripRenderer convention)
- bulbs: optional list of { dimmer, rgb } per cell for multi-bulb fixtures
"""

from __future__ import annotations

from typing import Any

from beartype import beartype

from parrot.fixtures.base import FixtureBase, FixtureGroup, FixtureWithBulbs
from parrot.fixtures.motionstrip import Motionstrip, Motionstrip38
from parrot.fixtures.moving_head import MovingHead


def _color_rgb(color: Any) -> tuple[float, float, float]:
    return (float(color.red), float(color.green), float(color.blue))


@beartype
def motionstrip_bar_pan_deg(fixture: FixtureBase) -> float:
    pan_dmx_value = float(fixture.values[0])
    if isinstance(fixture, Motionstrip38):
        pan_range = float(fixture.pan_range)
        if pan_range > 0:
            normalized_pan = (pan_dmx_value - float(fixture.pan_lower)) / pan_range
        else:
            normalized_pan = 0.0
    else:
        normalized_pan = pan_dmx_value / 255.0
    return -90.0 + (1.0 - normalized_pan) * 180.0


@beartype
def fixture_runtime_entry(fixture: FixtureBase) -> dict[str, Any] | None:
    cid = fixture.cloud_spec_id
    if cid is None:
        return None

    color = fixture.get_color()
    r, g, b = _color_rgb(color)
    dim = float(fixture.get_dimmer()) / 255.0
    entry: dict[str, Any] = {
        "id": cid,
        "dimmer": dim,
        "rgb": [r, g, b],
    }

    if isinstance(fixture, MovingHead):
        entry["pan_deg"] = float(fixture.get_pan_angle())
        entry["tilt_deg"] = float(fixture.get_tilt_angle())
    elif isinstance(fixture, Motionstrip):
        entry["bar_pan_deg"] = motionstrip_bar_pan_deg(fixture)

    if isinstance(fixture, FixtureWithBulbs):
        bulbs: list[dict[str, Any]] = []
        for bulb in fixture.get_bulbs():
            bc = bulb.get_color()
            br, bg, bb = _color_rgb(bc)
            bulbs.append(
                {
                    "dimmer": float(bulb.get_dimmer()) / 255.0,
                    "rgb": [br, bg, bb],
                }
            )
        entry["bulbs"] = bulbs

    return entry


@beartype
def iter_leaf_fixtures(
    runtime_patch: list[FixtureBase] | None,
    manual_group: Any | None,
) -> list[FixtureBase]:
    if runtime_patch is None:
        return []
    out: list[FixtureBase] = []
    for fixture in runtime_patch:
        if isinstance(fixture, FixtureGroup):
            out.extend(list(fixture.fixtures))
        else:
            out.append(fixture)
    if manual_group is not None:
        out.extend(list(manual_group.fixtures))
    return out


@beartype
def build_fixture_runtime_payload(
    runtime_patch: list[FixtureBase] | None,
    manual_group: Any | None,
) -> dict[str, Any]:
    fixtures: list[dict[str, Any]] = []
    for fixture in iter_leaf_fixtures(runtime_patch, manual_group):
        row = fixture_runtime_entry(fixture)
        if row is not None:
            fixtures.append(row)
    return {"version": 1, "fixtures": fixtures}
