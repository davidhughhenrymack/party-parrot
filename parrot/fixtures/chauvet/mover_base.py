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
        self.pan_lower = pan_lower / 540 * 255
        self.pan_upper = pan_upper / 540 * 255
        self.pan_range = self.pan_upper - self.pan_lower
        self.tilt_lower = tilt_lower / 270 * 255
        self.tilt_upper = tilt_upper / 270 * 255
        self.tilt_range = self.tilt_upper - self.tilt_lower
        self.dimmer_upper = dimmer_upper
        self.dmx_layout = dmx_layout
        self.color_wheel = color_wheel
        self.shutter_open_value = shutter_open
        self.strobe_shutter_lower = strobe_shutter_lower
        self.strobe_shutter_upper = strobe_shutter_upper
        self.disable_fine = disable_fine

        self.set_speed(speed_value)
        self.set_shutter_open()

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
        # Find in the gobo wheel
        acceptable_gobos = [i for i in self.gobo_wheel if i.name == name]
        if len(acceptable_gobos) == 0:
            raise ValueError(f"Unknown gobo {name}")

        gobo = acceptable_gobos[0]
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
