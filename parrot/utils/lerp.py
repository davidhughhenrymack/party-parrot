import time


def lerp(a, b, t):
    return a + (b - a) * t


def lerp_list(a, b, t):
    return [lerp(i, j, t) for i, j in zip(a, b)]


class Lerpable:
    def lerp(self, other, t):
        raise NotImplementedError()


class LerpAnimator:
    def __init__(self, subject: Lerpable, duration: float):
        self.subject = subject
        self.target = None
        self.duration = duration
        self.start_time = None

    def push(self, target):
        self.target = target
        self.start_time = time.time()

    def render(self):
        if self.target is None:
            return self.subject

        t = (time.time() - self.start_time) / self.duration
        if t > 1:
            self.subject = self.target
            self.target = None
            return self.subject

        return self.subject.lerp(self.target, t)
