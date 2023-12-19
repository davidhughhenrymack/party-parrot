
def lerp(a, b, t):
    return a + (b - a) * t

def lerp_list(a, b, t):
    return [lerp(i, j, t) for i, j in zip(a, b)]