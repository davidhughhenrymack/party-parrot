import time
from typing import Generic, TypeVar


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_list(a, b, t):
    return [lerp(i, j, t) for i, j in zip(a, b)]


T = TypeVar("T")


class Lerpable(Generic[T]):
    def lerp(self, other: T, t: float) -> T:
        raise NotImplementedError()


class LerpAnimator(Generic[T]):
    def __init__(self, subject: Lerpable[T], duration: float):
        self.subject = subject
        self.target = None
        self.duration = duration
        self.start_time = None

    def push(self, target: T):
        self.target = target
        self.start_time = time.time()

    def render(self) -> T:
        if self.target is None:
            return self.subject

        t = (time.time() - self.start_time) / self.duration
        if t > 1:
            self.subject = self.target
            self.target = None
            return self.subject

        return self.subject.lerp(self.target, t)
