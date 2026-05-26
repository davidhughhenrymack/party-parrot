from parrot.utils.lerp import LerpAnimator, Lerpable


class ScalarLerp(Lerpable["ScalarLerp"]):
    def __init__(self, value: float):
        self.value = value

    def lerp(self, other: "ScalarLerp", t: float) -> "ScalarLerp":
        return ScalarLerp(self.value + (other.value - self.value) * t)


def test_lerp_animator_push_starts_from_current_progress(monkeypatch):
    now = 0.0
    monkeypatch.setattr("parrot.utils.lerp.time.time", lambda: now)
    animator = LerpAnimator(ScalarLerp(0), duration=10)

    animator.push(ScalarLerp(10))
    now = 4.0
    assert animator.render().value == 4.0

    animator.push(ScalarLerp(20))

    assert animator.subject.value == 4.0
    assert animator.render().value == 4.0
    now = 9.0
    assert animator.render().value == 12.0
