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

    def to_dict(self) -> dict[str, object]:
        return {
            "key": self.key,
            "label": self.label,
            "default_options": dict(self.default_options),
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
    ),
    "par_rgb": FixtureTypeDefinition(
        key="par_rgb",
        label="LED Par RGB",
        builder=lambda spec: _apply_transform(
            ParRGB(spec.address, universe=_parse_universe(spec.universe)),
            spec,
        ),
    ),
    "par_rgbawu": FixtureTypeDefinition(
        key="par_rgbawu",
        label="Par RGBAWU",
        builder=lambda spec: _apply_transform(
            ParRGBAWU(spec.address, universe=_parse_universe(spec.universe)),
            spec,
        ),
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
    ),
    "five_beam_laser": FixtureTypeDefinition(
        key="five_beam_laser",
        label="Uking 5 Beam Laser",
        builder=lambda spec: _apply_transform(FiveBeamLaser(spec.address), spec),
    ),
    "two_beam_laser": FixtureTypeDefinition(
        key="two_beam_laser",
        label="Oultia 2 Beam Laser",
        builder=lambda spec: _apply_transform(TwoBeamLaser(spec.address), spec),
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
    ),
    "chauvet_slimpar_pro_h_7ch": FixtureTypeDefinition(
        key="chauvet_slimpar_pro_h_7ch",
        label="Chauvet SlimPAR Pro H 7Ch",
        builder=lambda spec: _apply_transform(ChauvetSlimParProH_7Ch(spec.address), spec),
    ),
    "chauvet_par_rgbawu": FixtureTypeDefinition(
        key="chauvet_par_rgbawu",
        label="Chauvet Par RGBAWU",
        builder=lambda spec: _apply_transform(ChauvetParRGBAWU(spec.address), spec),
    ),
    "chauvet_derby": FixtureTypeDefinition(
        key="chauvet_derby",
        label="Chauvet Derby",
        builder=lambda spec: _apply_transform(ChauvetDerby(spec.address), spec),
    ),
    "chauvet_rotosphere_28ch": FixtureTypeDefinition(
        key="chauvet_rotosphere_28ch",
        label="Chauvet Rotosphere 28Ch",
        builder=lambda spec: _apply_transform(ChauvetRotosphere_28Ch(spec.address), spec),
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
    ),
    "chauvet_colorband_pix_36ch": FixtureTypeDefinition(
        key="chauvet_colorband_pix_36ch",
        label="Chauvet ColorBand PiX 36Ch",
        builder=lambda spec: _apply_transform(
            ChauvetColorBandPiX_36Ch(spec.address),
            spec,
        ),
    ),
}


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


def degrees(value: float) -> float:
    return value * math.pi / 180.0
