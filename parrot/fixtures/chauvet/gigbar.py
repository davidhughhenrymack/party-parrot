from parrot.fixtures.chauvet.derby import ChauvetDerby
from parrot.fixtures.chauvet.move9 import ChauvetMove_9Ch
from parrot.fixtures.chauvet.par import ChauvetParRGBAWU
from parrot.fixtures.laser import Laser


class ChauvetGigbarLaser(Laser):
    def __init__(self, address):
        super().__init__(address, "gigbar laser", 1)

    def set_dimmer(self, value):
        self.values[0] = 6 if value > 0 else 0


def ChauvetGigBarMoveILS(address: int):
    return [
        ChauvetParRGBAWU(address),
        ChauvetParRGBAWU(address + 7),
        ChauvetDerby(address + 14),
        ChauvetDerby(address + 20),
        ChauvetGigbarLaser(address + 31),
        ChauvetMove_9Ch(address + 32),
        ChauvetMove_9Ch(address + 41),
    ]
