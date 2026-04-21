from typing import List
from parrot.fixtures.base import ColorWheelEntry, FixtureBase, GoboWheelEntry
from parrot.utils.color_extra import color_distance
from parrot.utils.colour import Color
from parrot.utils.dmx_utils import Universe
from parrot.fixtures.moving_head import MovingHead


class ChauvetMoverBase(MovingHead):
    def __init__(
        self,
        patch,
        name,
        width,
        dmx_layout,
        color_wheel: List[ColorWheelEntry],
        gobo_wheel: List[GoboWheelEntry],
        pan_lower=270,
        pan_upper=450,
        tilt_lower=0,
        tilt_upper=90,
        dimmer_upper=255,
        shutter_open=6,
        speed_value=0,
        strobe_shutter_lower=4,
        strobe_shutter_upper=76,
        disable_fine=False,
        universe=Universe.default,
    ):
        super().__init__(patch, name, width, gobo_wheel, universe)
        self.set_pan_tilt_range(pan_lower, pan_upper, tilt_lower, tilt_upper)
        self.dimmer_upper = dimmer_upper
        self.dmx_layout = dmx_layout
        self.color_wheel = color_wheel
        self.shutter_open_value = shutter_open
        self.strobe_shutter_lower = strobe_shutter_lower
        self.strobe_shutter_upper = strobe_shutter_upper
        self.disable_fine = disable_fine

        self.set_speed(speed_value)
        self.set_shutter_open()

    def set_pan_tilt_range(
        self,
        pan_lower: float,
        pan_upper: float,
        tilt_lower: float,
        tilt_upper: float,
    ) -> None:
        """Update mechanical pan/tilt limits in-place.

        Arguments are in degrees (same convention as the constructor): pan in
        [0, 540], tilt in [0, 270]. Recomputes the DMX-unit storage used by
        ``set_pan`` / ``set_tilt`` so live venue-editor edits take effect on
        the next frame without rebuilding the runtime scene.
        """
        self.pan_lower = float(pan_lower) / 540.0 * 255.0
        self.pan_upper = float(pan_upper) / 540.0 * 255.0
        self.pan_range = self.pan_upper - self.pan_lower
        self.tilt_lower = float(tilt_lower) / 270.0 * 255.0
        self.tilt_upper = float(tilt_upper) / 270.0 * 255.0
        self.tilt_range = self.tilt_upper - self.tilt_lower

    def set(self, name, value):
        if name in self.dmx_layout:
            if self.dmx_layout[name] <= self.width:
                self.values[self.dmx_layout[name]] = value

    def set_dimmer(self, value):
        super().set_dimmer(value)
        self.set("dimmer", value / 255 * self.dimmer_upper)

    # 0 - 255
    def set_pan(self, value):
        projected = self.pan_lower + (self.pan_range * value / 255)
        super().set_pan_angle(projected / 255 * 540)
        self.set("pan_coarse", int(projected))

        if not self.disable_fine:
            self.set("pan_fine", int((projected - self.values[0]) * 255))

    # 0 - 255
    def set_tilt(self, value):
        projected = self.tilt_lower + (self.tilt_range * value / 255)
        super().set_tilt_angle(projected / 255 * 270)

        self.set("tilt_coarse", int(projected))

        if not self.disable_fine:
            self.set("tilt_fine", int((projected - self.values[2]) * 255))

    def set_speed(self, value):
        self.set("speed", value)

    def set_color(self, color: Color):
        moderate = getattr(type(self), "COLOR_WHEEL_ROTATE_MODERATE_DMX", 0)
        if (
            getattr(self, "supports_color_wheel_rotate", False)
            and getattr(self, "_color_wheel_rotate", False)
            and isinstance(moderate, int)
            and moderate > 0
        ):
            self.set("color_wheel", moderate)
            FixtureBase.set_color(self, color)
            return
        # Find the closest color in the color wheel
        closest = None
        for entry in self.color_wheel:
            if closest == None or color_distance(entry.color, color) < color_distance(
                closest.color, color
            ):
                closest = entry

        # Set the color wheel value
        self.set("color_wheel", closest.dmx_value)
        super().set_color(closest.color)

    def set_gobo(self, name):
        # Find in the gobo wheel; unknown names fall back so interpreters never crash the app.
        acceptable_gobos = [i for i in self.gobo_wheel if i.name == name]
        if len(acceptable_gobos) > 0:
            gobo = acceptable_gobos[0]
        else:
            open_gobos = [i for i in self.gobo_wheel if i.name == "open"]
            if open_gobos:
                gobo = open_gobos[0]
            elif self.gobo_wheel:
                gobo = self.gobo_wheel[0]
            else:
                return
        self.set("gobo_wheel", gobo.dmx_value)

    def set_strobe(self, value):
        super().set_strobe(value)
        # Use accumulated strobe_value for DMX output and logic
        strobe = self.strobe_value

        if strobe < 10:
            self.set_shutter_open()
            return

        lower = self.strobe_shutter_lower
        upper = self.strobe_shutter_upper
        scaled = lower + (upper - lower) * strobe / 255
        self.set("shutter", scaled)

    def set_shutter_open(self):
        self.set("shutter", self.shutter_open_value)

    def set_focus(self, value: float) -> None:
        """Write focus value to the "focus" DMX channel (big → small = 0 → 255)."""
        super().set_focus(value)
        self.set("focus", int(round(self.focus_value * 255)))

    def set_prism(self, on: bool, rotate_speed: float = 0.0) -> None:
        """Map (on, rotate_speed) onto the Prism 1 (7-facet) DMX channel.

        Hybrid 140SR prism1 value ranges (both 19ch and 13ch layouts):
            000–007: no prism
            008–012: static prism on
            013–130: forward rotation, slow → fast
            131–247: reverse rotation, slow → fast
            248–255: static prism on
        """
        super().set_prism(on, rotate_speed)
        if not self.prism_on:
            self.set("prism1", 0)
            return

        speed = self.prism_rotate_speed
        if speed == 0.0:
            # Static prism on — use the mid-range static plateau value.
            self.set("prism1", 10)
        elif speed > 0.0:
            # Forward rotation: 13 (slowest) → 130 (fastest)
            self.set("prism1", int(round(13 + (130 - 13) * speed)))
        else:
            # Reverse rotation: 131 (slowest) → 247 (fastest)
            self.set("prism1", int(round(131 + (247 - 131) * (-speed))))
