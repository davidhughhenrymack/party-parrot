from enum import Enum


Mode = Enum(
    "Mode",
    ["rave", "blackout", "chill", "rave_gentle", "test", "ethereal"],
)


# Canonical ordering of lighting modes by hype/intensity, lowest to highest.
# This is the single source of truth for UI listings (remote + desktop) and
# for up/down keyboard navigation. Keep it in sync with ``Mode`` — every mode
# must appear exactly once. ``test`` slots just above ``blackout`` because it
# is a diagnostic/calm checkout rig, not a dance look.
MODES_BY_HYPE: list[Mode] = [
    Mode.blackout,
    Mode.test,
    Mode.chill,
    Mode.ethereal,
    Mode.rave_gentle,
    Mode.rave,
]

assert set(MODES_BY_HYPE) == set(Mode), (
    "MODES_BY_HYPE must list every Mode exactly once"
)
assert len(MODES_BY_HYPE) == len(set(MODES_BY_HYPE)) == len(Mode), (
    "MODES_BY_HYPE must have no duplicates"
)
