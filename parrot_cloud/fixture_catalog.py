from __future__ import annotations

from dataclasses import dataclass, field
import math
from typing import Callable

import numpy as np
from beartype import beartype

from parrot.fixtures.base import FixtureBase, FixtureGroup, ManualGroup
from parrot.fixtures.chauvet.colorband_pix import ChauvetColorBandPiX_36Ch
from parrot.fixtures.chauvet.derby import ChauvetDerby
from parrot.fixtures.chauvet.intimidator110 import ChauvetSpot110_12Ch
from parrot.fixtures.chauvet.intimidator160 import ChauvetSpot160_12Ch
from parrot.fixtures.chauvet.intimidator_hybrid_140sr import (
    ChauvetIntimidatorHybrid140SR_13Ch,
    ChauvetIntimidatorHybrid140SR_19Ch,
)
from parrot.fixtures.chauvet.move9 import ChauvetMove_9Ch
from parrot.fixtures.chauvet.par import ChauvetParRGBAWU
from parrot.fixtures.chauvet.rogue_beam_r2 import ChauvetRogueBeamR2
from parrot.fixtures.chauvet.rotosphere import ChauvetRotosphere_28Ch
from parrot.fixtures.chauvet.slimpar_pro_h import ChauvetSlimParProH_7Ch
from parrot.fixtures.chauvet.slimpar_pro_q import ChauvetSlimParProQ_5Ch
from parrot.fixtures.led_par import ParRGB, ParRGBAWU
from parrot.fixtures.motionstrip import Motionstrip38
from parrot.fixtures.oultia.laser import TwoBeamLaser
from parrot.fixtures.uking.laser import FiveBeamLaser
from parrot.utils.dmx_utils import Universe
from parrot.vj.renderers.base import quaternion_from_axis_angle, quaternion_multiply
from parrot_cloud.domain import FixtureSpec, VenueSnapshot


@beartype
@dataclass(frozen=True)
class FixtureTypeDefinition:
    key: str
    label: str
    builder: Callable[[FixtureSpec], FixtureBase]
    default_options: dict[str, int | float | bool] = field(default_factory=dict)
    # DMX channel footprint (matches desktop FixtureBase width).
    dmx_address_width: int = 1

    def to_dict(self) -> dict[str, object]:
        return {
            "key": self.key,
            "label": self.label,
            "default_options": dict(self.default_options),
            "dmx_address_width": self.dmx_address_width,
        }


def _parse_universe(value: str) -> Universe:
    try:
        return Universe(value)
    except ValueError:
        return Universe.default


def _option_bool(spec: FixtureSpec, key: str, default: bool = False) -> bool:
    return bool(spec.options.get(key, default))


def _option_float(spec: FixtureSpec, key: str, default: float) -> float:
    return float(spec.options.get(key, default))


def _rotation_to_quaternion(
    rotation_x: float, rotation_y: float, rotation_z: float
) -> np.ndarray:
    x_quat = quaternion_from_axis_angle(np.array([1.0, 0.0, 0.0]), rotation_x)
    y_quat = quaternion_from_axis_angle(np.array([0.0, 1.0, 0.0]), rotation_y)
    z_quat = quaternion_from_axis_angle(np.array([0.0, 0.0, 1.0]), rotation_z)
    return quaternion_multiply(z_quat, quaternion_multiply(y_quat, x_quat))


def _apply_transform(fixture: FixtureBase, spec: FixtureSpec) -> FixtureBase:
    fixture.x = spec.x
    fixture.y = spec.y
    fixture.z = spec.z
    fixture.orientation = _rotation_to_quaternion(
        spec.rotation_x, spec.rotation_y, spec.rotation_z
    )
    fixture.cloud_spec_id = spec.id
    fixture.cloud_fixture_type = spec.fixture_type
    fixture.cloud_group_name = spec.group_name
    fixture.cloud_is_manual = spec.is_manual
    return fixture


FIXTURE_TYPES: dict[str, FixtureTypeDefinition] = {
    "manual_dimmer_channel": FixtureTypeDefinition(
        key="manual_dimmer_channel",
        label="Manual Dimmer Channel",
        builder=lambda spec: _apply_transform(
            FixtureBase(
                spec.address,
                spec.name or "Manual Dimmer",
                int(_option_float(spec, "width", 1.0)),
                universe=_parse_universe(spec.universe),
            ),
            spec,
        ),
        default_options={"width": 1},
        dmx_address_width=1,
    ),
    "par_rgb": FixtureTypeDefinition(
        key="par_rgb",
        label="LED Par RGB",
        builder=lambda spec: _apply_transform(
            ParRGB(spec.address, universe=_parse_universe(spec.universe)),
            spec,
        ),
        dmx_address_width=7,
    ),
    "par_rgbawu": FixtureTypeDefinition(
        key="par_rgbawu",
        label="Par RGBAWU",
        builder=lambda spec: _apply_transform(
            ParRGBAWU(spec.address, universe=_parse_universe(spec.universe)),
            spec,
        ),
        dmx_address_width=9,
    ),
    "chauvet_spot_110": FixtureTypeDefinition(
        key="chauvet_spot_110",
        label="Chauvet Intimidator 110/120",
        builder=lambda spec: _apply_transform(
            ChauvetSpot110_12Ch(
                spec.address,
                pan_lower=_option_float(spec, "pan_lower", 270.0),
                pan_upper=_option_float(spec, "pan_upper", 450.0),
                tilt_lower=_option_float(spec, "tilt_lower", 0.0),
                tilt_upper=_option_float(spec, "tilt_upper", 90.0),
                dimmer_upper=_option_float(spec, "dimmer_upper", 255.0),
                universe=_parse_universe(spec.universe),
            ),
            spec,
        ),
        dmx_address_width=12,
    ),
    "chauvet_spot_160": FixtureTypeDefinition(
        key="chauvet_spot_160",
        label="Chauvet Intimidator 160",
        builder=lambda spec: _apply_transform(
            ChauvetSpot160_12Ch(
                spec.address,
                pan_lower=_option_float(spec, "pan_lower", 360.0),
                pan_upper=_option_float(spec, "pan_upper", 540.0),
                tilt_lower=_option_float(spec, "tilt_lower", 0.0),
                tilt_upper=_option_float(spec, "tilt_upper", 90.0),
                dimmer_upper=_option_float(spec, "dimmer_upper", 255.0),
                universe=_parse_universe(spec.universe),
            ),
            spec,
        ),
        dmx_address_width=11,
    ),
    "chauvet_rogue_beam_r2": FixtureTypeDefinition(
        key="chauvet_rogue_beam_r2",
        label="Chauvet Rogue Beam R2",
        builder=lambda spec: _apply_transform(
            ChauvetRogueBeamR2(
                spec.address,
                pan_lower=_option_float(spec, "pan_lower", 270.0),
                pan_upper=_option_float(spec, "pan_upper", 450.0),
                tilt_lower=_option_float(spec, "tilt_lower", 0.0),
                tilt_upper=_option_float(spec, "tilt_upper", 90.0),
                dimmer_upper=_option_float(spec, "dimmer_upper", 200.0),
                universe=_parse_universe(spec.universe),
            ),
            spec,
        ),
        dmx_address_width=15,
    ),
    "chauvet_intimidator_hybrid_140sr": FixtureTypeDefinition(
        key="chauvet_intimidator_hybrid_140sr",
        label="Chauvet Intimidator Hybrid 140SR (19ch)",
        builder=lambda spec: _apply_transform(
            ChauvetIntimidatorHybrid140SR_19Ch(
                spec.address,
                pan_lower=_option_float(spec, "pan_lower", 0.0),
                pan_upper=_option_float(spec, "pan_upper", 540.0),
                tilt_lower=_option_float(spec, "tilt_lower", 0.0),
                tilt_upper=_option_float(spec, "tilt_upper", 270.0),
                dimmer_upper=_option_float(spec, "dimmer_upper", 255.0),
                universe=_parse_universe(spec.universe),
            ),
            spec,
        ),
        default_options={
            "pan_lower": 0,
            "pan_upper": 540,
            "tilt_lower": 0,
            "tilt_upper": 270,
        },
        dmx_address_width=19,
    ),
    "chauvet_intimidator_hybrid_140sr_13ch": FixtureTypeDefinition(
        key="chauvet_intimidator_hybrid_140sr_13ch",
        label="Chauvet Intimidator Hybrid 140SR (13ch)",
        builder=lambda spec: _apply_transform(
            ChauvetIntimidatorHybrid140SR_13Ch(
                spec.address,
                pan_lower=_option_float(spec, "pan_lower", 0.0),
                pan_upper=_option_float(spec, "pan_upper", 540.0),
                tilt_lower=_option_float(spec, "tilt_lower", 0.0),
                tilt_upper=_option_float(spec, "tilt_upper", 270.0),
                dimmer_upper=_option_float(spec, "dimmer_upper", 255.0),
                universe=_parse_universe(spec.universe),
            ),
            spec,
        ),
        default_options={
            "pan_lower": 0,
            "pan_upper": 540,
            "tilt_lower": 0,
            "tilt_upper": 270,
        },
        dmx_address_width=13,
    ),
    "motionstrip_38": FixtureTypeDefinition(
        key="motionstrip_38",
        label="Motionstrip 38",
        default_options={"pan_lower": 0, "pan_upper": 255, "invert_pan": False},
        builder=lambda spec: _apply_transform(
            Motionstrip38(
                spec.address,
                pan_lower=int(_option_float(spec, "pan_lower", 0.0)),
                pan_upper=int(_option_float(spec, "pan_upper", 255.0)),
                invert_pan=_option_bool(spec, "invert_pan", False),
                universe=_parse_universe(spec.universe),
            ),
            spec,
        ),
        dmx_address_width=38,
    ),
    "five_beam_laser": FixtureTypeDefinition(
        key="five_beam_laser",
        label="Uking 5 Beam Laser",
        builder=lambda spec: _apply_transform(FiveBeamLaser(spec.address), spec),
        dmx_address_width=13,
    ),
    "two_beam_laser": FixtureTypeDefinition(
        key="two_beam_laser",
        label="Oultia 2 Beam Laser",
        builder=lambda spec: _apply_transform(TwoBeamLaser(spec.address), spec),
        dmx_address_width=10,
    ),
    "chauvet_slimpar_pro_q_5ch": FixtureTypeDefinition(
        key="chauvet_slimpar_pro_q_5ch",
        label="Chauvet SlimPAR Pro Q 5Ch",
        builder=lambda spec: _apply_transform(
            ChauvetSlimParProQ_5Ch(
                spec.address, universe=_parse_universe(spec.universe)
            ),
            spec,
        ),
        dmx_address_width=5,
    ),
    "chauvet_slimpar_pro_h_7ch": FixtureTypeDefinition(
        key="chauvet_slimpar_pro_h_7ch",
        label="Chauvet SlimPAR Pro H 7Ch",
        builder=lambda spec: _apply_transform(ChauvetSlimParProH_7Ch(spec.address), spec),
        dmx_address_width=7,
    ),
    "chauvet_par_rgbawu": FixtureTypeDefinition(
        key="chauvet_par_rgbawu",
        label="Chauvet Par RGBAWU",
        builder=lambda spec: _apply_transform(ChauvetParRGBAWU(spec.address), spec),
        dmx_address_width=7,
    ),
    "chauvet_derby": FixtureTypeDefinition(
        key="chauvet_derby",
        label="Chauvet Derby",
        builder=lambda spec: _apply_transform(ChauvetDerby(spec.address), spec),
        dmx_address_width=6,
    ),
    "chauvet_rotosphere_28ch": FixtureTypeDefinition(
        key="chauvet_rotosphere_28ch",
        label="Chauvet Rotosphere 28Ch",
        builder=lambda spec: _apply_transform(ChauvetRotosphere_28Ch(spec.address), spec),
        dmx_address_width=28,
    ),
    "chauvet_move_9ch": FixtureTypeDefinition(
        key="chauvet_move_9ch",
        label="Chauvet Move 9Ch",
        builder=lambda spec: _apply_transform(
            ChauvetMove_9Ch(
                spec.address,
                pan_lower=_option_float(spec, "pan_lower", 270.0),
                pan_upper=_option_float(spec, "pan_upper", 450.0),
                tilt_lower=_option_float(spec, "tilt_lower", 0.0),
                tilt_upper=_option_float(spec, "tilt_upper", 90.0),
                dimmer_upper=_option_float(spec, "dimmer_upper", 255.0),
            ),
            spec,
        ),
        dmx_address_width=12,
    ),
    "chauvet_colorband_pix_36ch": FixtureTypeDefinition(
        key="chauvet_colorband_pix_36ch",
        label="Chauvet ColorBand PiX 36Ch",
        builder=lambda spec: _apply_transform(
            ChauvetColorBandPiX_36Ch(spec.address),
            spec,
        ),
        dmx_address_width=36,
    ),
}


@beartype
def dmx_address_width_for_fixture(
    fixture_type: str, options: dict[str, object]
) -> int:
    """DMX footprint for spacing cloned fixtures (matches FixtureBase.width)."""
    if fixture_type == "manual_dimmer_channel":
        return max(1, int(float(options.get("width", 1))))
    definition = FIXTURE_TYPES.get(fixture_type)
    if definition is None:
        return 1
    return definition.dmx_address_width


def list_fixture_types() -> list[dict[str, object]]:
    return [definition.to_dict() for definition in FIXTURE_TYPES.values()]


def create_fixture_instance(spec: FixtureSpec) -> FixtureBase:
    definition = FIXTURE_TYPES.get(spec.fixture_type)
    if definition is None:
        raise KeyError(f"Unsupported fixture type: {spec.fixture_type}")
    fixture = definition.builder(spec)
    if spec.name:
        fixture.name = spec.name
    return fixture


def build_runtime_fixture_groups(snapshot: VenueSnapshot) -> tuple[list[FixtureBase], ManualGroup | None]:
    grouped: dict[str, list[FixtureBase]] = {}
    ungrouped: list[FixtureBase] = []
    manual_fixtures: list[FixtureBase] = []

    for spec in snapshot.fixtures:
        fixture = create_fixture_instance(spec)
        if spec.is_manual:
            manual_fixtures.append(fixture)
            continue
        if spec.group_name:
            grouped.setdefault(spec.group_name, []).append(fixture)
            continue
        ungrouped.append(fixture)

    runtime_fixtures: list[FixtureBase] = []
    runtime_fixtures.extend(ungrouped)
    for group_name, fixtures in grouped.items():
        if len(fixtures) == 1:
            runtime_fixtures.append(fixtures[0])
        else:
            runtime_fixtures.append(FixtureGroup(fixtures, group_name))

    manual_group = None
    if manual_fixtures:
        manual_group = ManualGroup(manual_fixtures, f"{snapshot.summary.name} Manual Control")

    return runtime_fixtures, manual_group


def update_runtime_fixture_transforms(
    runtime_fixtures: list[FixtureBase],
    manual_group: ManualGroup | None,
    snapshot: VenueSnapshot,
) -> bool:
    current_fixtures: list[FixtureBase] = []
    for fixture in runtime_fixtures:
        if isinstance(fixture, FixtureGroup):
            current_fixtures.extend(list(fixture.fixtures))
        else:
            current_fixtures.append(fixture)
    if manual_group is not None:
        current_fixtures.extend(list(manual_group.fixtures))

    current_by_id = {
        getattr(fixture, "cloud_spec_id", None): fixture for fixture in current_fixtures
    }
    if None in current_by_id:
        return False

    if len(current_by_id) != len(snapshot.fixtures):
        return False

    for spec in snapshot.fixtures:
        fixture = current_by_id.get(spec.id)
        if fixture is None:
            return False
        if getattr(fixture, "cloud_fixture_type", None) != spec.fixture_type:
            return False
        if getattr(fixture, "cloud_group_name", None) != spec.group_name:
            return False
        if getattr(fixture, "cloud_is_manual", None) != spec.is_manual:
            return False
        if fixture.address != spec.address:
            return False
        if fixture.universe != _parse_universe(spec.universe):
            return False

    for spec in snapshot.fixtures:
        fixture = current_by_id[spec.id]
        _apply_transform(fixture, spec)
        if spec.name:
            fixture.name = spec.name

    return True


def degrees(value: float) -> float:
    return value * math.pi / 180.0
