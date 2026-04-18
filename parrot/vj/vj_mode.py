#!/usr/bin/env python3

from enum import StrEnum

from beartype import beartype


class VJMode(StrEnum):
    """Visual presets for the concert stage.

    Enum order drives LEFT/RIGHT arrow navigation in the keyboard handler and the
    remote control UI.

    ``prom_*`` entries are DJ-branded sparkle scenes. The Zombie Rave (``zr_*``)
    entries are commented out while we're off-season — re-enable the block below
    to restore them.
    """

    blackout = "blackout"
    prom_dmack = "prom_dmack"
    prom_wufky = "prom_wufky"
    prom_mayhem = "prom_mayhem"
    prom_thunderbunny = "prom_thunderbunny"
    # --- Zombie Rave (Halloween) presets — commented out for now ---
    # zr_golden_age = "zr_golden_age"
    # zr_music_vids = "zr_music_vids"
    # zr_hiphop = "zr_hiphop"
    # zr_early_rave = "zr_early_rave"
    # zr_full_rave = "zr_full_rave"


# Accept historic strings from persisted cloud control-state. zr_* entries are
# disabled in the enum above, so we coerce them onto the default prom scene
# rather than crashing on boot when loading an old DB row.
_LEGACY_VJ_MODE_NAMES: dict[str, str] = {
    "full_rave": "prom_dmack",
    "early_rave": "prom_dmack",
    "golden_age": "prom_dmack",
    "music_vids": "prom_dmack",
    "hiphop": "prom_dmack",
    "zr_full_rave": "prom_dmack",
    "zr_early_rave": "prom_dmack",
    "zr_golden_age": "prom_dmack",
    "zr_music_vids": "prom_dmack",
    "zr_hiphop": "prom_dmack",
}


@beartype
def parse_vj_mode_string(raw: str) -> VJMode:
    """Resolve persisted or cloud control-state strings (incl. disabled zr_* legacy)."""
    key = _LEGACY_VJ_MODE_NAMES.get(raw.strip(), raw.strip())
    return VJMode(key)


_PROM_DJ_LABELS: dict[VJMode, str] = {
    VJMode.prom_dmack: "Prom · dmack",
    VJMode.prom_wufky: "Prom · wufky",
    VJMode.prom_mayhem: "Prom · mayhem",
    VJMode.prom_thunderbunny: "Prom · thunderbunny",
}


@beartype
def vj_mode_menu_label(mode: VJMode) -> str:
    """Human-readable label for menu bar and remote UI."""
    if mode == VJMode.blackout:
        return "Blackout"
    if mode in _PROM_DJ_LABELS:
        return _PROM_DJ_LABELS[mode]
    name = mode.name
    if name.startswith("zr_"):
        rest = name[3:].replace("_", " ").title()
        return f"Zombie Rave · {rest}"
    return str(mode.value).replace("_", " ").title()
