from parrot.fixtures.base import FixtureBase
from parrot.utils.color_extra import color_distance
from parrot.utils.colour import Color
from parrot.fixtures.moving_head import MovingHead


class ChauvetSpot_12Ch(MovingHead):

    def __init__(
        self,
        patch,
        name,
        width,
        dmx_layout,
        color_wheel,
        gobo_wheel,
        pan_lower=270,
        pan_upper=450,
        tilt_lower=0,
        tilt_upper=90,
        dimmer_upper=255,
    ):
        super().__init__(patch, name, width)
        self.pan_lower = pan_lower / 540 * 255
        self.pan_upper = pan_upper / 540 * 255
        self.pan_range = self.pan_upper - self.pan_lower
        self.tilt_lower = tilt_lower / 270 * 255
        self.tilt_upper = tilt_upper / 270 * 255
        self.tilt_range = self.tilt_upper - self.tilt_lower
        self.dimmer_upper = dimmer_upper
        self.dmx_layout = dmx_layout
        self.color_wheel = color_wheel
        self.gobo_wheel = gobo_wheel

        self.set_speed(0)
        self.set_shutter_open()

    def set(self, name, value):
        if name in self.dmx_layout:
            if self.dmx_layout[name] <= self.width:
                self.values[self.dmx_layout[name]] = value

    def set_dimmer(self, value):
        self.set("dimmer", value / 255 * self.dimmer_upper)

    # 0 - 255
    def set_pan(self, value):
        projected = self.pan_lower + (self.pan_range * value / 255)
        self.set("pan_coarse", int(projected))
        self.set("pan_fine", int((projected - self.values[0]) * 255))

    # 0 - 255
    def set_tilt(self, value):
        projected = self.tilt_lower + (self.tilt_range * value / 255)
        self.set("tilt_coarse", int(projected))
        self.set("tilt_fine", int((projected - self.values[2]) * 255))

    def set_speed(self, value):
        self.set("speed", value)

    def set_color(self, color: Color):
        super().set_color(color)
        # Find the closest color in the color wheel
        closest = None
        for entry in self.color_wheel:
            if closest == None or color_distance(entry.color, color) < color_distance(
                closest.color, color
            ):
                closest = entry

        # Set the color wheel value
        self.set("color_wheel", closest.dmx_value)

    def set_gobo(self, name):
        # Find in the gobo wheel
        gobo = next(i for i in self.gobo_wheel if i.name == name)
        self.set("gobo", gobo.dmx_value)

    def set_strobe(self, value):
        lower = 4
        upper = 76
        scaled = lower + (upper - lower) * value / 255
        self.set("shutter", scaled)

    def set_shutter_open(self):
        self.set("shutter", 6)
