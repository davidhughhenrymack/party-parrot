from typing import List
from parrot.fixtures.base import FixtureBase, GoboWheelEntry
from parrot.utils.dmx_utils import Universe


class MovingHead(FixtureBase):
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

    def set_pan_angle(self, value):
        self.pan_angle = value

    def get_pan_angle(self):
        return self.pan_angle

    def set_tilt_angle(self, value):
        self.tilt_angle = value

    def get_tilt_angle(self):
        return self.tilt_angle

    @property
    def gobo_wheel(self):
        return self._gobo_wheel
