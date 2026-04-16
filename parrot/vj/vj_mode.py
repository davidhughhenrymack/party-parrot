#!/usr/bin/env python3

from enum import StrEnum

from beartype import beartype


class VJMode(StrEnum):
    """Visual presets for the concert stage. `zr_*` = Zombie Rave event; `blackout` is generic."""

    blackout = "blackout"
    prom_dmack = "prom_dmack"
    zr_golden_age = "zr_golden_age"
    zr_music_vids = "zr_music_vids"
    zr_hiphop = "zr_hiphop"
    zr_early_rave = "zr_early_rave"
    zr_full_rave = "zr_full_rave"


_LEGACY_VJ_MODE_NAMES: dict[str, str] = {
    "full_rave": "zr_full_rave",
    "early_rave": "zr_early_rave",
    "golden_age": "zr_golden_age",
    "music_vids": "zr_music_vids",
    "hiphop": "zr_hiphop",
}


@beartype
def parse_vj_mode_string(raw: str) -> VJMode:
    """Resolve persisted or cloud control-state strings (includes pre-zr_* names)."""
    key = _LEGACY_VJ_MODE_NAMES.get(raw.strip(), raw.strip())
    return VJMode(key)


@beartype
def vj_mode_menu_label(mode: VJMode) -> str:
    """Human-readable label for menu bar and remote UI."""
    if mode == VJMode.blackout:
        return "Blackout"
    if mode == VJMode.prom_dmack:
        return "Prom · dmack"
    name = mode.name
    if name.startswith("zr_"):
        rest = name[3:].replace("_", " ").title()
        return f"Zombie Rave · {rest}"
    return str(mode.value).replace("_", " ").title()
