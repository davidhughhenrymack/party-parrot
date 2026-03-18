import enum
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from beartype import beartype

from parrot.fixtures.base import FixtureBase, FixtureGroup, ManualGroup
from parrot.fixtures.chauvet.intimidator110 import ChauvetSpot110_12Ch
from parrot.fixtures.chauvet.intimidator160 import ChauvetSpot160_12Ch
from parrot.fixtures.chauvet.rogue_beam_r2 import ChauvetRogueBeamR2
from parrot.fixtures.chauvet.slimpar_pro_q import ChauvetSlimParProQ_5Ch
from parrot.fixtures.led_par import ParRGB, ParRGBAWU
from parrot.fixtures.motionstrip import Motionstrip38
from parrot.fixtures.oultia.laser import TwoBeamLaser
from parrot.fixtures.uking.laser import FiveBeamLaser
from parrot.utils.dmx_utils import Universe

venues = enum.Enum(
    "Venues", ["dmack", "mtn_lotus", "truckee_theatre", "crux_test", "big"]
)


@beartype
@dataclass(frozen=True)
class CustomVenue:
    name: str
    display_name: str


DEFAULT_FLOOR_SIZE_FEET = 10.0
DEFAULT_VIDEO_WALL = {
    "x": 0.0,
    "y": 3.0,
    "z": -4.5,
    "width": 10.0,
    "height": 6.0,
}
EDITOR_CONFIG_PATH = Path("venue_editor.json")

SUPPORTED_EDITOR_FIXTURE_TYPES = {
    "ParRGB": "LED Par RGB",
    "ParRGBAWU": "LED Par RGBAWU",
    "Motionstrip38": "Motionstrip 38",
    "ChauvetSpot110_12Ch": "Chauvet Intimidator 110",
    "ChauvetSpot160_12Ch": "Chauvet Intimidator 160",
    "ChauvetSlimParProQ_5Ch": "Chauvet SlimPAR Pro Q",
    "ChauvetRogueBeamR2": "Chauvet Rogue Beam R2",
    "TwoBeamLaser": "Oultia 2 Beam Laser",
    "FiveBeamLaser": "Uking 5 Beam Laser",
}

manual_groups: dict[Any, ManualGroup | None] = {}
venue_patches: dict[Any, list[FixtureBase | FixtureGroup]] = {}
custom_venues_by_name: dict[str, CustomVenue] = {}
venue_defaults: dict[Any, dict[str, Any]] = {}


def _fixture(
    fixture_type: str,
    address: int,
    universe: str = Universe.default.value,
    **kwargs: Any,
) -> dict[str, Any]:
    spec = {
        "kind": "fixture",
        "type": fixture_type,
        "address": int(address),
        "universe": universe,
    }
    spec.update(kwargs)
    return spec


def _group(name: str, fixtures: list[dict[str, Any]]) -> dict[str, Any]:
    return {"kind": "group", "name": name, "fixtures": fixtures}


def _default_patch_specs() -> dict[Any, list[dict[str, Any]]]:
    return {
        venues.dmack: [
            _fixture("ChauvetSpot160_12Ch", 1),
            _fixture("ChauvetSpot110_12Ch", 140),
            *[_fixture("ParRGB", i) for i in range(12, 48, 7)],
            _fixture("Motionstrip38", 154, pan_lower=0, pan_upper=256, invert_pan=True),
            _fixture("Motionstrip38", 59, pan_lower=0, pan_upper=256, invert_pan=True),
            _fixture("FiveBeamLaser", 100),
            _fixture("TwoBeamLaser", 120),
        ],
        venues.mtn_lotus: [
            *[
                _fixture("ParRGBAWU", i, universe=Universe.art1.value)
                for i in range(10, 90, 10)
            ],
            _fixture("Motionstrip38", 90, pan_lower=0, pan_upper=256),
            _fixture("ParRGB", 195),
            _fixture("ParRGB", 205),
            _fixture("ChauvetSpot160_12Ch", 182),
            _fixture("TwoBeamLaser", 220),
            _fixture("Motionstrip38", 130, pan_lower=0, pan_upper=256),
            _fixture("ParRGB", 230),
            _fixture("ParRGB", 238),
            _fixture("ChauvetSpot110_12Ch", 170),
        ],
        venues.truckee_theatre: [
            _group(
                "Sidelights",
                [
                    *[
                        _fixture("ChauvetSlimParProQ_5Ch", i)
                        for i in range(154, 170, 5)
                    ],
                    *[
                        _fixture("ChauvetSlimParProQ_5Ch", i)
                        for i in range(174, 190, 5)
                    ],
                ],
            ),
            _group(
                "Front led wash",
                [
                    _fixture("ChauvetSlimParProQ_5Ch", i)
                    for i in range(30, 66, 5)
                ],
            ),
            _group(
                "Moving heads crescent",
                [
                    *[
                        _fixture("ChauvetRogueBeamR2", i)
                        for i in range(191, 191 + 15 * 6, 15)
                    ],
                    *[_fixture("ParRGB", i) for i in range(67, 67 + 6 * 7, 7)],
                ],
            ),
            _group(
                "Mirror ball",
                [
                    _fixture("ChauvetSpot160_12Ch", 1),
                    _fixture("ChauvetSpot110_12Ch", 13),
                    _fixture("ParRGB", 450),
                    _fixture("ParRGB", 460),
                ],
            ),
            _group(
                "Motion strip (doubled)",
                [
                    _fixture("Motionstrip38", 300, pan_lower=128, pan_upper=256),
                    _fixture("Motionstrip38", 338, pan_lower=128, pan_upper=256),
                ],
            ),
            _group(
                "Spare Pars",
                [_fixture("ParRGB", i) for i in range(400, 400 + 4 * 7, 7)],
            ),
        ],
        venues.crux_test: [
            _group(
                "Rogue Beams",
                [_fixture("ChauvetRogueBeamR2", 1), _fixture("ChauvetRogueBeamR2", 16)],
            ),
        ],
        venues.big: [
            *[_fixture("ChauvetSpot160_12Ch", i) for i in range(10, 90, 10)],
            *[_fixture("ChauvetSpot160_12Ch", i) for i in range(100, 180, 10)],
            *[_fixture("ChauvetSpot160_12Ch", i) for i in range(200, 400, 12)],
        ],
    }


def _default_manual_group_specs() -> dict[Any, list[dict[str, Any]]]:
    return {
        venues.truckee_theatre: [
            _fixture("FixtureBase", i, name=f"Manual Bulb {i}", width=1)
            for i in range(1, 9)
        ],
        venues.mtn_lotus: [
            _fixture(
                "FixtureBase",
                1,
                universe=Universe.art1.value,
                name="SR spot",
                width=1,
            ),
            _fixture(
                "FixtureBase",
                2,
                universe=Universe.art1.value,
                name="SL spot",
                width=1,
            ),
        ],
    }


def _read_editor_config() -> dict[str, Any]:
    if not EDITOR_CONFIG_PATH.exists():
        return {"custom_venues": {}, "fixture_additions": {}}
    with EDITOR_CONFIG_PATH.open("r") as handle:
        data = json.load(handle)
    return {
        "custom_venues": data.get("custom_venues", {}),
        "fixture_additions": data.get("fixture_additions", {}),
    }


def _write_editor_config(data: dict[str, Any]) -> None:
    with EDITOR_CONFIG_PATH.open("w") as handle:
        json.dump(data, handle, indent=2)


def _universe_from_spec(spec: dict[str, Any]) -> Universe:
    return Universe(spec.get("universe", Universe.default.value))


def _instantiate_fixture(spec: dict[str, Any]) -> FixtureBase:
    fixture_type = spec["type"]
    address = int(spec["address"])
    universe = _universe_from_spec(spec)

    if fixture_type == "ParRGB":
        return ParRGB(address, universe=universe)
    if fixture_type == "ParRGBAWU":
        return ParRGBAWU(address, universe=universe)
    if fixture_type == "Motionstrip38":
        return Motionstrip38(
            address,
            pan_lower=int(spec.get("pan_lower", 0)),
            pan_upper=int(spec.get("pan_upper", 255)),
            invert_pan=bool(spec.get("invert_pan", False)),
            universe=universe,
        )
    if fixture_type == "ChauvetSpot110_12Ch":
        return ChauvetSpot110_12Ch(address, universe=universe)
    if fixture_type == "ChauvetSpot160_12Ch":
        return ChauvetSpot160_12Ch(address, universe=universe)
    if fixture_type == "ChauvetSlimParProQ_5Ch":
        return ChauvetSlimParProQ_5Ch(address, universe=universe)
    if fixture_type == "ChauvetRogueBeamR2":
        return ChauvetRogueBeamR2(address, universe=universe)
    if fixture_type == "TwoBeamLaser":
        return TwoBeamLaser(address)
    if fixture_type == "FiveBeamLaser":
        return FiveBeamLaser(address)
    if fixture_type == "FixtureBase":
        return FixtureBase(
            address,
            spec.get("name", f"Fixture {address}"),
            int(spec.get("width", 1)),
            universe=universe,
        )
    raise ValueError(f"Unsupported fixture type '{fixture_type}'")


def _instantiate_item(spec: dict[str, Any]) -> FixtureBase | FixtureGroup:
    if spec.get("kind") == "group":
        return FixtureGroup(
            [_instantiate_fixture(fixture_spec) for fixture_spec in spec["fixtures"]],
            spec["name"],
        )
    return _instantiate_fixture(spec)


def _ensure_custom_venue(venue_name: str, display_name: str) -> CustomVenue:
    existing = custom_venues_by_name.get(venue_name)
    if existing is not None:
        return existing
    venue = CustomVenue(name=venue_name, display_name=display_name)
    custom_venues_by_name[venue_name] = venue
    return venue


def _refresh_patch_state() -> None:
    editor_config = _read_editor_config()
    patch_specs = _default_patch_specs()
    manual_specs = _default_manual_group_specs()
    configured_custom_names = set(editor_config["custom_venues"].keys())

    venue_patches.clear()
    manual_groups.clear()
    venue_defaults.clear()
    for custom_name in list(custom_venues_by_name.keys()):
        if custom_name not in configured_custom_names:
            del custom_venues_by_name[custom_name]

    for builtin_venue in venues:
        additions = editor_config["fixture_additions"].get(builtin_venue.name, [])
        combined_specs = [*patch_specs.get(builtin_venue, []), *additions]
        venue_patches[builtin_venue] = [_instantiate_item(spec) for spec in combined_specs]
        manual_spec = manual_specs.get(builtin_venue)
        manual_groups[builtin_venue] = (
            ManualGroup(
                [_instantiate_fixture(spec) for spec in manual_spec],
                f"{get_venue_display_name(builtin_venue)} Manual Control",
            )
            if manual_spec
            else None
        )
        venue_defaults[builtin_venue] = {
            "floor_size_feet": DEFAULT_FLOOR_SIZE_FEET,
            "video_wall": dict(DEFAULT_VIDEO_WALL),
        }

    for venue_name, venue_data in editor_config["custom_venues"].items():
        display_name = venue_data.get("display_name", venue_name)
        custom_venue = _ensure_custom_venue(venue_name, display_name)
        venue_patches[custom_venue] = [
            _instantiate_item(spec) for spec in venue_data.get("fixtures", [])
        ]
        manual_groups[custom_venue] = None
        venue_defaults[custom_venue] = {
            "floor_size_feet": float(
                venue_data.get("default_floor_size_feet", DEFAULT_FLOOR_SIZE_FEET)
            ),
            "video_wall": dict(DEFAULT_VIDEO_WALL),
        }


def _slugify_venue_name(display_name: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", display_name.strip().lower()).strip("_")
    return slug or "venue"


@beartype
def get_supported_fixture_types() -> list[tuple[str, str]]:
    return list(SUPPORTED_EDITOR_FIXTURE_TYPES.items())


@beartype
def get_all_venues() -> list[Any]:
    return [*list(venues), *custom_venues_by_name.values()]


@beartype
def get_venue_display_name(venue: Any) -> str:
    display_name = getattr(venue, "display_name", None)
    if isinstance(display_name, str) and display_name:
        return display_name
    return venue.name.replace("_", " ").title()


@beartype
def resolve_venue(name: str) -> Any | None:
    for builtin_venue in venues:
        if builtin_venue.name == name:
            return builtin_venue
    return custom_venues_by_name.get(name)


@beartype
def get_default_venue_metadata(venue: Any) -> dict[str, Any]:
    defaults = venue_defaults.get(
        venue,
        {"floor_size_feet": DEFAULT_FLOOR_SIZE_FEET, "video_wall": dict(DEFAULT_VIDEO_WALL)},
    )
    return {
        "floor_size_feet": float(defaults["floor_size_feet"]),
        "video_wall": dict(defaults["video_wall"]),
    }


@beartype
def add_custom_venue(display_name: str) -> CustomVenue:
    cleaned_name = display_name.strip()
    if not cleaned_name:
        raise ValueError("Venue name cannot be empty")

    editor_config = _read_editor_config()
    venue_name = _slugify_venue_name(cleaned_name)
    if resolve_venue(venue_name) is not None:
        raise ValueError(f"Venue '{cleaned_name}' already exists")

    editor_config["custom_venues"][venue_name] = {
        "display_name": cleaned_name,
        "fixtures": [],
        "default_floor_size_feet": DEFAULT_FLOOR_SIZE_FEET,
    }
    _write_editor_config(editor_config)
    _refresh_patch_state()
    return custom_venues_by_name[venue_name]


@beartype
def add_fixture_to_venue(venue: Any, fixture_type: str, address: int) -> FixtureBase:
    if fixture_type not in SUPPORTED_EDITOR_FIXTURE_TYPES:
        raise ValueError(f"Unsupported fixture type '{fixture_type}'")
    if address < 1 or address > 512:
        raise ValueError("Fixture address must be between 1 and 512")

    editor_config = _read_editor_config()
    fixture_spec = _fixture(fixture_type, address)

    if isinstance(venue, CustomVenue):
        venue_entry = editor_config["custom_venues"].get(venue.name)
        if venue_entry is None:
            raise ValueError(f"Unknown custom venue '{venue.name}'")
        venue_entry.setdefault("fixtures", []).append(fixture_spec)
    else:
        editor_config["fixture_additions"].setdefault(venue.name, []).append(fixture_spec)

    _write_editor_config(editor_config)
    _refresh_patch_state()

    for item in venue_patches[venue]:
        if isinstance(item, FixtureGroup):
            for fixture in item.fixtures:
                if type(fixture).__name__ == fixture_type and fixture.address == address:
                    return fixture
        elif type(item).__name__ == fixture_type and item.address == address:
            return item

    raise RuntimeError("New fixture could not be found after adding it")


@beartype
def get_manual_group(venue: Any) -> ManualGroup | None:
    return manual_groups.get(venue)


@beartype
def has_manual_dimmer(venue: Any) -> bool:
    return manual_groups.get(venue) is not None


@beartype
def reload_patch_bay_configuration() -> None:
    _refresh_patch_state()


_refresh_patch_state()
