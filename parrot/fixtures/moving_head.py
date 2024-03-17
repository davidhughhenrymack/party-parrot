from parrot.fixtures.base import FixtureBase


class MovingHead(FixtureBase):
    def __init__(self, address, name, width):
        super().__init__(address, name, width)
