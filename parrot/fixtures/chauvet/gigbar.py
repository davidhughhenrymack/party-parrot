from parrot.fixtures.chauvet.derby import ChauvetDerby
from parrot.fixtures.chauvet.move9 import ChauvetMove_9Ch
from parrot.fixtures.chauvet.par import ChauvetParRGBAWU


def ChauvetGigBarMoveILS(address: int):
    return [
        ChauvetParRGBAWU(address),
        ChauvetParRGBAWU(address + 7),
        ChauvetDerby(address + 14),
        ChauvetDerby(address + 20),
        ChauvetMove_9Ch(address + 32),
        ChauvetMove_9Ch(address + 41),
    ]
