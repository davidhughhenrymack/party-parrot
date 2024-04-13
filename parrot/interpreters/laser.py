from parrot.interpreters.latched import DimmerFadeLatched
from parrot.interpreters.base import with_args


LaserLatch = with_args(DimmerFadeLatched, new_has_rainbow=False, new_hype=60)
