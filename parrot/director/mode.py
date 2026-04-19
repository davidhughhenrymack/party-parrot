from enum import Enum


Mode = Enum(
    "Mode",
    ["rave", "blackout", "chill", "test", "ethereal", "stroby"],
)


# Canonical ordering of lighting modes by hype/intensity, lowest to highest.
# This is the single source of truth for UI listings (remote + desktop) and
# for up/down keyboard navigation. Keep it in sync with ``Mode`` — every mode
# must appear exactly once. ``test`` sits at the very bottom (below
# ``blackout``) so operators can step DOWN into a diagnostic checkout rig
# from blackout, and never accidentally land in ``test`` while walking the
# hype ladder up from the stage-dark state. ``ethereal`` comes before
# ``chill`` (lower hype than chill).
MODES_BY_HYPE: list[Mode] = [
    Mode.test,
    Mode.blackout,
    Mode.ethereal,
    Mode.chill,
    Mode.rave,
    Mode.stroby,
]

assert set(MODES_BY_HYPE) == set(Mode), (
    "MODES_BY_HYPE must list every Mode exactly once"
)
assert len(MODES_BY_HYPE) == len(set(MODES_BY_HYPE)) == len(Mode), (
    "MODES_BY_HYPE must have no duplicates"
)
