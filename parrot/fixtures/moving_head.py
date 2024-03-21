from parrot.fixtures.base import FixtureBase


class MovingHead(FixtureBase):
    def __init__(self, address, name, width):
        super().__init__(address, name, width)
        self.pan_angle = 0
        self.tilt_angle = 0

    def set_pan_angle(self, value):
        self.pan_angle = value

    def get_pan_angle(self):
        return self.pan_angle

    def set_tilt_angle(self, value):
        self.tilt_angle = value

    def get_tilt_angle(self):
        return self.tilt_angle
