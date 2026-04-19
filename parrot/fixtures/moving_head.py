from typing import List
from parrot.fixtures.base import FixtureBase, GoboWheelEntry
from parrot.utils.dmx_utils import Universe


class MovingHead(FixtureBase):
    # Per-model rendering capabilities. Subclasses override these when the
    # physical fixture genuinely has no prism or no variable-focus optic —
    # the desktop and web renderers skip the matching visual effects so a
    # fixture like the Chauvet Rogue Beam R2 (no prism accessory, no focus
    # travel on its optic) doesn't fake a splay-fan or tight-beam look in
    # preview. DMX-facing `set_prism` / `set_focus` still exist on every
    # subclass so interpreters can remain uniform.
    supports_prism: bool = True
    supports_focus: bool = True

    def __init__(
        self,
        address,
        name,
        width,
        gobo_wheel: List[GoboWheelEntry],
        universe=Universe.default,
    ):
        super().__init__(address, name, width, universe)
        self.pan_angle = 0
        self.tilt_angle = 0
        self._gobo_wheel = gobo_wheel
        # Prism state (boolean on/off + rotate speed in [-1, 1]; 0 = static prism on).
        # Supported on all MovingHead subclasses even if the physical fixture has no
        # prism — subclasses with a prism channel override set_prism to write DMX.
        self.prism_on: bool = False
        self.prism_rotate_speed: float = 0.0
        # Rotating gobo wheel state (separate from the static gobo wheel).
        # ``rotating_gobo_slot`` is 0 for open/beam, 1+ picks a rotating-wheel gobo.
        # ``rotating_gobo_rotate_speed`` in [-1, 1]; 0 = static (no rotation).
        # Subclasses with a physical rotating gobo wheel override set_rotating_gobo
        # to emit DMX; fixtures without one still accept the call as a no-op.
        self.rotating_gobo_slot: int = 0
        self.rotating_gobo_rotate_speed: float = 0.0
        # Focus: 0.0 = big/wide (out-of-focus, broad beam),
        # 1.0 = small/tight (in-focus, pinpoint). Subclasses with a focus
        # channel override set_focus to emit DMX.
        self.focus_value: float = 0.0

    def set_pan_angle(self, value):
        self.pan_angle = value

    def get_pan_angle(self):
        return self.pan_angle

    def set_tilt_angle(self, value):
        self.tilt_angle = value

    def get_tilt_angle(self):
        return self.tilt_angle

    def set_prism(self, on: bool, rotate_speed: float = 0.0) -> None:
        """Set prism state. ``rotate_speed`` is clamped to [-1, 1]; 0 = static prism on."""
        self.prism_on = bool(on)
        if rotate_speed > 1.0:
            rotate_speed = 1.0
        elif rotate_speed < -1.0:
            rotate_speed = -1.0
        self.prism_rotate_speed = float(rotate_speed)

    def get_prism(self) -> tuple[bool, float]:
        return self.prism_on, self.prism_rotate_speed

    def set_rotating_gobo(self, slot: int, rotate_speed: float = 0.0) -> None:
        """Select a rotating-gobo slot (0 = open/beam) and spin speed in [-1, 1]."""
        self.rotating_gobo_slot = max(0, int(slot))
        if rotate_speed > 1.0:
            rotate_speed = 1.0
        elif rotate_speed < -1.0:
            rotate_speed = -1.0
        self.rotating_gobo_rotate_speed = float(rotate_speed)

    def get_rotating_gobo(self) -> tuple[int, float]:
        return self.rotating_gobo_slot, self.rotating_gobo_rotate_speed

    def set_focus(self, value: float) -> None:
        """Set focus in [0.0, 1.0]. 0 = big/wide beam, 1 = tight/small."""
        if value < 0.0:
            value = 0.0
        elif value > 1.0:
            value = 1.0
        self.focus_value = float(value)

    def get_focus(self) -> float:
        return self.focus_value

    @property
    def gobo_wheel(self):
        return self._gobo_wheel
